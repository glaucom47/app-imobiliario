"""
Serviço de Processamento e Importação em Lote de Consultores da Equipa (Excel / CSV).
Suporta ficheiros .xlsx (OpenXML) nativamente através da biblioteca padrão (zipfile/xml.etree)
e ficheiros .csv com delimitadores universais (; e ,) e codificações variadas (UTF-8, Latin-1).
"""
import base64
import csv
import io
import re
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
import zipfile

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.team_import_schema import (
    TeamImportResponse,
    TeamImportRowDetail,
)
from app.services.auth_service import hash_password
from app.services import billing_service


class TeamImportService:
    """Motor de leitura e importação resiliente de ficheiros de folha de cálculo."""

    @classmethod
    def gerar_modelo_csv(cls) -> str:
        """Gera um modelo de exemplo em formato CSV compatível diretamente com Excel."""
        linhas = [
            "Nome;Email;Telemóvel;Palavra-passe",
            "Ana Santos;ana.santos@exemplo.pt;912345678;Fecho2026!",
            "Carlos Silva;carlos.silva@exemplo.pt;923456789;Fecho2026!",
            "Mariana Costa;mariana.costa@exemplo.pt;934567890;",
        ]
        return "\ufeff" + "\r\n".join(linhas) + "\r\n"

    @classmethod
    def _coluna_letra_para_indice(cls, col_str: str) -> int:
        """Converte letras de coluna Excel (A, B, ..., Z, AA, AB) em índice zero-based."""
        idx = 0
        for char in col_str.upper():
            if 'A' <= char <= 'Z':
                idx = idx * 26 + (ord(char) - ord('A') + 1)
        return max(0, idx - 1)

    @classmethod
    def parse_xlsx(cls, file_bytes: bytes) -> List[Dict[str, str]]:
        """
        Extrai linhas e colunas de ficheiros .xlsx utilizando unicamente bibliotecas padrão do Python.
        """
        if not file_bytes:
            return []

        try:
            zf = zipfile.ZipFile(io.BytesIO(file_bytes))
        except Exception as exc:
            raise ValueError(f"Ficheiro Excel corrompido ou inválido: {exc}")

        # 1. Extração da tabela de strings partilhadas (xl/sharedStrings.xml)
        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            try:
                ss_tree = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                # Remove namespaces para consulta simplificada
                for si in ss_tree.iter():
                    if si.tag.endswith("si"):
                        # Pode conter <t> direto ou múltiplos <r><t>
                        textos = [elem.text for elem in si.iter() if elem.tag.endswith("t") and elem.text]
                        shared_strings.append("".join(textos))
            except Exception:
                pass

        # 2. Localiza as folhas de cálculo (worksheets)
        worksheet_names = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
        worksheet_names.sort()

        if not worksheet_names:
            return []

        # Lê a primeira folha com dados
        linhas_matriz: List[List[str]] = []
        try:
            ws_tree = ET.fromstring(zf.read(worksheet_names[0]))
            for row in ws_tree.iter():
                if row.tag.endswith("row"):
                    colunas: Dict[int, str] = {}
                    max_col = 0
                    for c in row.iter():
                        if c.tag.endswith("c"):
                            r_coord = c.get("r", "")
                            match = re.match(r"([A-Za-z]+)", r_coord)
                            col_idx = cls._coluna_letra_para_indice(match.group(1)) if match else len(colunas)
                            max_col = max(max_col, col_idx)

                            t_attr = c.get("t", "")
                            val = ""
                            v_elem = next((el for el in c if el.tag.endswith("v")), None)
                            if v_elem is not None and v_elem.text:
                                if t_attr == "s":
                                    s_idx = int(v_elem.text)
                                    val = shared_strings[s_idx] if 0 <= s_idx < len(shared_strings) else ""
                                else:
                                    val = v_elem.text
                            elif t_attr == "inlineStr":
                                is_t = [el.text for el in c.iter() if el.tag.endswith("t") and el.text]
                                val = "".join(is_t)

                            colunas[col_idx] = (val or "").strip()

                    if colunas:
                        linha_preenchida = [colunas.get(i, "") for i in range(max_col + 1)]
                        # Só adiciona se houver algum valor preenchido na linha
                        if any(linha_preenchida):
                            linhas_matriz.append(linha_preenchida)
        except Exception as exc:
            raise ValueError(f"Não foi possível ler as células da folha Excel: {exc}")

        return cls._normalizar_matriz_para_dicionarios(linhas_matriz)

    @classmethod
    def parse_csv(cls, text: str) -> List[Dict[str, str]]:
        """Analisa texto CSV detectando delimitadores e cabeçalhos automaticamente."""
        if not text or not text.strip():
            return []

        # Remove BOM se presente
        limpo = text.lstrip("\ufeff")

        # Detecta delimitador (, ou ; ou \t)
        primeira_linha = limpo.split("\n", 1)[0]
        delimitador = ";" if primeira_linha.count(";") >= primeira_linha.count(",") else ","
        if primeira_linha.count("\t") > primeira_linha.count(delimitador):
            delimitador = "\t"

        reader = csv.reader(io.StringIO(limpo), delimiter=delimitador)
        linhas_matriz: List[List[str]] = []
        for row in reader:
            if any(cell.strip() for cell in row):
                linhas_matriz.append([cell.strip() for cell in row])

        return cls._normalizar_matriz_para_dicionarios(linhas_matriz)

    @classmethod
    def _normalizar_matriz_para_dicionarios(cls, matriz: List[List[str]]) -> List[Dict[str, str]]:
        """Mapeia uma matriz de linhas para dicionários normalizados com chaves nome, email, telemovel, password."""
        if not matriz:
            return []

        header_idx = -1
        idx_nome = -1
        idx_email = -1
        idx_tel = -1
        idx_pwd = -1

        # Procura a linha que contém cabeçalho (com 'nome', 'email', etc.)
        for i, row in enumerate(matriz):
            row_lower = [str(c).lower().strip() for c in row]
            for j, val in enumerate(row_lower):
                if any(w in val for w in ("nome", "consultor", "colaborador", "membro")) and idx_nome == -1:
                    idx_nome = j
                elif any(w in val for w in ("email", "e-mail", "correio")) and idx_email == -1:
                    idx_email = j
                elif any(w in val for w in ("telemovel", "telemóvel", "telefone", "contacto", "contato", "phone")) and idx_tel == -1:
                    idx_tel = j
                elif any(w in val for w in ("senha", "password", "palavra-passe", "passe")) and idx_pwd == -1:
                    idx_pwd = j

            if idx_nome != -1 and idx_email != -1:
                header_idx = i
                break

        # Se não encontrou cabeçalho explícito com 'nome' e 'email', tenta adivinhar pelas primeiras colunas
        if header_idx == -1:
            idx_nome = 0
            idx_email = 1
            idx_tel = 2 if len(matriz[0]) > 2 else -1
            idx_pwd = 3 if len(matriz[0]) > 3 else -1
            dados_linhas = matriz
        else:
            dados_linhas = matriz[header_idx + 1:]

        resultado: List[Dict[str, str]] = []
        for row in dados_linhas:
            nome = row[idx_nome] if 0 <= idx_nome < len(row) else ""
            email = row[idx_email] if 0 <= idx_email < len(row) else ""
            tel = row[idx_tel] if 0 <= idx_tel < len(row) else ""
            pwd = row[idx_pwd] if 0 <= idx_pwd < len(row) else ""

            # Se o email não estiver na coluna esperada, mas estiver em outra, localiza por regex
            if "@" not in email:
                for cell in row:
                    if "@" in cell and "." in cell:
                        email = cell
                        break

            # Se a linha contiver pelo menos nome ou email preenchidos, inclui
            if nome.strip() or email.strip():
                resultado.append({
                    "nome": nome.strip(),
                    "email": email.strip().lower(),
                    "telemovel": tel.strip() if tel else "",
                    "password": pwd.strip() if pwd else "",
                })

        return resultado

    @classmethod
    def extrair_linhas_de_payload(
        cls,
        file_base64: Optional[str] = None,
        filename: Optional[str] = None,
        csv_text: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Recebe o payload (base64 ou texto) e converte em lista padronizada de dicionários."""
        if csv_text and csv_text.strip():
            return cls.parse_csv(csv_text)

        if not file_base64:
            return []

        # Remove eventual prefixo de DataURL (ex: data:application/vnd.openxmlformats-officedocument...;base64,)
        b64_data = file_base64
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]

        try:
            raw_bytes = base64.b64decode(b64_data)
        except Exception as exc:
            raise ValueError(f"Não foi possível descodificar o ficheiro base64: {exc}")

        nome_arq = (filename or "").lower()
        if nome_arq.endswith(".xlsx") or raw_bytes.startswith(b"PK\x03\x04"):
            return cls.parse_xlsx(raw_bytes)

        # Tentativa com CSV em múltiplos encodings
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                texto = raw_bytes.decode(enc)
                return cls.parse_csv(texto)
            except UnicodeDecodeError:
                continue

        raise ValueError("Formato de ficheiro não reconhecido. Por favor envie um ficheiro .xlsx ou .csv.")

    @classmethod
    def import_team(
        cls,
        db: Session,
        current_user: User,
        rows: List[Dict[str, str]],
        default_password: str = "Fecho2026!",
    ) -> TeamImportResponse:
        """
        Processa a lista de consultores e insere os novos registos na base de dados com Bcrypt rounds=12.
        Garante isolamento multi-tenant, validação e verificação de limites do plano da agência.
        """
        agencia_id = current_user.agencia_id
        tenant = current_user.tenant or db.query(Tenant).filter(Tenant.id == agencia_id).first()

        detalhes: List[TeamImportRowDetail] = []
        total_criados = 0
        total_ignorados = 0

        # Conjunto de e-mails já processados nesta mesma importação (evita duplicatas internas da planilha)
        emails_vistos = set()

        for num_linha, item in enumerate(rows, start=1):
            nome = (item.get("nome") or "").strip()
            email = (item.get("email") or "").strip().lower()
            telemovel = (item.get("telemovel") or "").strip() or None
            senha = (item.get("password") or "").strip() or default_password

            # Validações básicas de formato
            if not nome or len(nome) < 2:
                detalhes.append(TeamImportRowDetail(
                    linha=num_linha,
                    nome=nome or "Desconhecido",
                    email=email or "sem-email",
                    telemovel=telemovel,
                    status="invalido",
                    motivo="Nome ausente ou com menos de 2 caracteres.",
                ))
                total_ignorados += 1
                continue

            if not email or "@" not in email or "." not in email:
                detalhes.append(TeamImportRowDetail(
                    linha=num_linha,
                    nome=nome,
                    email=email or "sem-email",
                    telemovel=telemovel,
                    status="invalido",
                    motivo="Endereço de e-mail inválido ou mal formatado.",
                ))
                total_ignorados += 1
                continue

            if email in emails_vistos:
                detalhes.append(TeamImportRowDetail(
                    linha=num_linha,
                    nome=nome,
                    email=email,
                    telemovel=telemovel,
                    status="ignorado_existente",
                    motivo="E-mail duplicado na própria planilha.",
                ))
                total_ignorados += 1
                continue

            emails_vistos.add(email)

            # Verifica se o e-mail já existe na base de dados
            user_existente = db.query(User).filter(func.lower(User.email) == email).first()
            if user_existente:
                detalhes.append(TeamImportRowDetail(
                    linha=num_linha,
                    nome=nome,
                    email=email,
                    telemovel=telemovel,
                    status="ignorado_existente",
                    motivo="Já existe um utilizador registado com este e-mail no sistema.",
                ))
                total_ignorados += 1
                continue

            # Verifica limite de utilizadores do plano da agência (vitalício permite até 10+)
            if not billing_service.pode_adicionar_utilizador(db, tenant):
                detalhes.append(TeamImportRowDetail(
                    linha=num_linha,
                    nome=nome,
                    email=email,
                    telemovel=telemovel,
                    status="limite_atingido",
                    motivo=billing_service.LIMITE_UTILIZADORES_MSG,
                ))
                total_ignorados += 1
                continue

            # Cria o novo consultor
            novo_consultor = User(
                agencia_id=agencia_id,
                nome=nome,
                email=email,
                telemovel=telemovel,
                role="consultor",
                password_hash=hash_password(senha),
                ativo=True,
            )
            db.add(novo_consultor)
            db.flush()

            detalhes.append(TeamImportRowDetail(
                linha=num_linha,
                nome=nome,
                email=email,
                telemovel=telemovel,
                status="criado",
                motivo=None,
            ))
            total_criados += 1

        if total_criados > 0:
            db.commit()

        msg = f"Importação concluída: {total_criados} consultores criados com sucesso"
        if total_ignorados > 0:
            msg += f" ({total_ignorados} ignorados por duplicidade ou formato)."
        else:
            msg += "."

        return TeamImportResponse(
            total_lidos=len(rows),
            total_criados=total_criados,
            total_ignorados=total_ignorados,
            detalhes=detalhes,
            mensagem=msg,
        )
