import os
import re
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

# --- Debug flag (enable by setting env JOBCLASS_DEBUG=1) ---
DEBUG = os.getenv("JOBCLASS_DEBUG", "0") == "1"

def _dbg(msg: str):
    if DEBUG:
        print(msg)

# ==========================
# Category labels (normalized slashes)
# ==========================
CATEGORY_LABELS = {
    "Engineering": "Engineering",
    "Production / Operations / Quality": "Production/Operations/Quality",
    "Package Design or Development / Brand Management": "Package Design or Development/Brand Management",
    "Plant Management": "Plant Management",
    "Logistics / Supply Chain Management": "Logistics/Supply Chain Management",
    "Regulatory Affairs / Validation / Compliance": "Regulatory Affairs/Validation/Compliance",
    "Procurement": "Procurement",
    "Sales": "Sales",
    "CEO / General Manager / Other Senior Management": "CEO/General Manager/Other Senior Management",
    "Other": "Other",
}

# ==========================
# Executive normalization & list
# ==========================
EXEC_TITLES = [
    "ceo", "cfo", "cmo", "svp", "vp", "vice president", "president", "presidente",
    "chief executive officer", "chief financial officer", "executive",
    "owner", "founder", "partner", "principal", "gm", "directora",
    "director", "manager", "general manager", "executive manager", "treasurer", "board",
    "finance director", "director finance", "director of finance",
    "vp finance", "vice president finance", "svp finance", "senior vice president finance",
    "head of finance", "finance executive", "gerente", "finance supervisor",
]

ASSISTANT_EXCLUSIONS = ["assistant", "coordinator"]

# ==========================
# Undesirable patterns (Other)
# ==========================
UNDESIRABLE_PATTERNS = [
    r"\badministrative\b", r"\bevents\b", "administrativa", r"\badministrative manager\b", r"\badministrative director\b", r"\badmin\b", r"\badmin manager\b", r"\badmin\.?\b", r"\badmin\w*\s+director\b",

    # Non-qualifying engineer titles
    r"\bsoftware engineer\b", r"\bcivil engineer\b",
    r"\bstructural engineer\b", r"\bchemical engineer\b",

    # Non-qualifying operations titles
    r"\barea operations\b", r"\bpayroll operations\b", r"\bclinical operations\b", r"\bpackaging specialist\b",
    r"\bcomputer operations\b", r"\bclient operations\b", r"\bpackaging technologist\b",
    r"\bcommercial operations\b", r"\bfield operations\b", r"\bgraphics\b", r"\bgrant\b",
    r"\bsecurity and operations\b", r"\bfranchise operations\b", r"\bbusiness development\b",
    r"\bservice operations\b", r"\bservice manager\b", r"\bfleet operations\b",
    r"\btrial operations\b", r"\brental operations\b", r"\byacht operations\b",
    r"\bvessel operations\b", r"\badvertising operations\b", r"\bbranch operations\b",
    r"\bcampus operations\b", r"\bchannel operations\b", r"\boffice operations\b",
    r"\bbilling operations\b", r"\bregional operations\b", r"\bart director\b", r"\bsocial media\b", r"\bpre\s*press\b",

    r"\bdietitian\b", r"\bnutritionist\b", r"\bdispatcher\b", r"\bdoctor\b",
    r"\bdriver\b", r"\bprofessor\b", r"\blecturer\b", r"\binstructor\b",
    r"\bstudent\b", r"\bpostdoctoral\b", r"\bteacher\b", r"\bintern\b",
    r"\bemt\b", r"\bems\b", r"\bambulance\b", r"\bcontent manager\b", r"\bwife\b", r"\bagency\b", r"\bagency manager\b",

    r"\bpersonnel\b", r"\binformation systems\b", r"\bchief technology officer\b",
    r"\binventory control\b", r"\binvestor\b", r"\blab\b",
    r"\bjanitor\b", r"\bmd\b", r"\beditor\b", r"\bjournalist\b",
    r"\bmedia\b", r"\bpublisher\b", r"\bwriter\b", r"\bmedical director\b",
    r"\bmember\b", r"\bnurse\b", r"\boffice manager\b", r"\bbusiness analyst\b",
    r"\badministrator\b", r"\badministrative assistant\b", r"\bclerk\b",
    r"\bpharm tech\b", r"\bpharmacist\b", r"\bpharmacy manager\b",
    r"\bpharmacy director\b", r"\bplanner\b", r"\bprepress manager\b",
    r"\bpressman\b", r"\bpricing\b", r"\bprogrammer\b", r"\bproprietor\b",
    r"\breceptionist\b", r"\brecruiter\b", r"\bregional manager\b",
    r"\bregistered agent\b", r"\bscientist\b",
    r"\bsoftware developer\b", r"\bstore manager\b", r"\bstore director\b",
    r"\bveterinarian\b", r"\bprint manager\b", r"\bpublic relations\b",

    # Consultants
    r"\bconsultant\b",

    # Broad non-qualifying titles
    r"\baccount manager\b", r"\bacc manager\b", r"\baccout manager\b", r"\blegal\b",
    r"\banalyst\b", r"\btooling\b", r"\battorney\b", r"\bauditor\b",
    r"\bbartender\b", r"\bbookkeeper\b", r"\bbusiness development\b",
    r"\bchairman\b", r"\bchemist\b", r"\bclinical\b", r"\bcommunications\b",

    # Customer-facing roles
    r"\bcustomer service\b", r"\bcustomer support\b", r"\bcustomer experience\b", r"\bcustomer success\b",
    r"\bcx\b", r"\bcx manager\b", r"\bcx director\b", r"\bcx lead\b", r"\bcx head\b", r"\bcx executive\b",
    r"\bcustomer exp\.?\b", r"\bclient support\b", r"\bclient services?\b",
    r"\bclient experience\b", r"\bclient relations?\b", r"\bclient relationship(s)?\b",

    # HR / People leadership
    r"\bhuman resources\b", r"\bhr director\b", r"\bdirector hr\b",
    r"\bdirector of hr\b", r"\bdirector human resources\b",
    r"\bdirector of human resources\b", r"\bhuman resources director\b",
    r"\bvp hr\b", r"\bvice president hr\b", r"\bsvp hr\b",
    r"\bsenior vice president hr\b", r"\bhead of hr\b",
    r"\bhr executive\b", r"\bhr supervisor\b",
    r"\bvp human resources\b", r"\bvice president human resources\b",
    r"\bsvp human resources\b", r"\bhead of human resources\b",
    r"\bchief human resources officer\b", r"\bchro\b",
    r"\bpeople operations\b", r"\btalent acquisition\b",
    r"\bpeople director\b", r"\bhr manager\b", r"\bdirector people\b", "agent",

    # Design roles (excluding packaging/product design)
    r"\b3d\s+designer?\b",
    r"\bgraphic\s+design",
    r"\bweb\s+design",
    r"\bart\s+design",
    r"\bart\s+designer?\b",
    r"\bcreative\s+designer?\b",
    r"\bdesign\s+agency\b",
    r"\bdesign\s+associate\b",
    r"\bdesign\s+professional\b",
    r"\bweb\s+and\s+graphic\s+designer?\b",
    r"\bux\s+designer?\b",
    r"\bui\s+designer?\b",
    r"\bdigital\s+designer?\b",
    r"\bvisual\s+designer?\b",
    r"\bdesign\s*/\s*sales\b",
    r"\bdesign\s*&\s*project\s+manager\b",
    r"\bdesign\s+and\s+project\s+manager\b",
    r"\bcorporate\s+design\b",
]

# IT roles (force → Other)
UNDESIRABLE_PATTERNS += [
    r"(?<![a-z])\b(i\.?t\.?)\b(?![a-z])",
    r"(?<![a-z])\bit\b(?![a-z])(?:\s*[&/,\-]?\s*\b[\w&]+){0,6}",
    r"\binformation\s+tech(nology)?\b",
    r"\bchief\s+information\s+officer\b",
    r"\bcio\b",
]

# ==========================
# Category keyword heuristics
# ==========================
CATEGORY_KEYWORDS = {
    "Sales": [
        "sales", "sale", "account executive", "account director", "sls",
        "commercial manager", "director sales", "director of sales", "sales director",
        "vp sales", "vice president sales", "rsm", "regional sales manager", "svp sales",
        "senior vice president sales", "head of sales", "sales executive", "sales supervisor",
        "ventas", "venta", "sales engineer", "territory manager",
    ],
    "Engineering": [
        "engineer", "engineering", "instrumentation", "engineering technician",
        "plant engineer", "staff engineer", "continuous improvement engineer",
        "engineering systems manager", "engineering technologist",
        "plant support engineer", "corporate engineer", "asset engineer",
        "project engineer", "manufacturing engineer", "manufacturing systems engineer",
        "integration engineer", "operations engineer", "principal engineer",
        "process engineer", "process control engineer", "production engineer", "packaging engineer",
        "sr pkg eng", "sr mgr pkg eng",
        "director engineering", "director of engineering", "engineering director",
        "vp engineering", "vice president engineering", "svp engineering",
        "senior vice president engineering", "head of engineering",
        "engineering executive", "engineering supervisor", "ingeniero", "ingenieria",
    ],
    "Regulatory Affairs / Validation / Compliance": [
        "food safety", "safety", "compliance", "regulatory", "validation",
        "government relations",
        "director regulatory", "director of regulatory", "regulatory director",
        "vp regulatory", "vice president regulatory", "svp regulatory",
        "senior vice president regulatory", "head of regulatory",
        "regulatory executive", "regulatory supervisor", "director compliance",
        "director of compliance", "compliance director", "vp compliance",
        "vice president compliance", "svp compliance",
        "senior vice president compliance", "head of compliance",
        "compliance executive", "compliance supervisor", "director food safety",
        "vp food safety", "vice president food safety", "head of food safety",
    ],
    "Package Design or Development / Brand Management": [
        "packaging", "package", "packaging maintenance", "packaging technicial", "category",
        "packaging manager", "packaging supervisor", "brand", "marketing", "product development",
        "rd", "innovation", "category", "product", "commerical", "creative director", "cmo", "chief marketing officer",
        "director marketing", "director of marketing", "marketing director",
        "vp marketing", "vice president marketing", "svp marketing",
        "senior vice president marketing", "head of marketing",
        "marketing executive", "marketing supervisor", "director brand",
        "brand director", "vp brand", "vice president brand", "svp brand",
        "head of brand", "brand executive", "brand supervisor",
        "director product", "product director", "vp product",
        "vice president product", "svp product", "head of product",
        "product executive", "product supervisor", "director r&d",
        "director of r&d", "rd director", "vp r&d", "vice president r&d",
        "svp r&d", "head of r&d", "rd executive", "rd supervisor", "empaque", "empaques",
    ],
    "Logistics / Supply Chain Management": [
        "logistics", "supply chain", "warehouse", "shipping", "distribution",
        "transportation", "receiving", "fulfillment", "inventory",
        "director logistics", "director of logistics", "logistics director",
        "vp logistics", "vice president logistics", "svp logistics",
        "senior vice president logistics", "head of logistics",
        "logistics executive", "logistics supervisor",
        "director supply chain", "director of supply chain", "supply chain director",
        "vp supply chain", "vice president supply chain", "svp supply chain",
        "senior vice president supply chain", "head of supply chain",
        "supply chain executive", "supply chain supervisor", "logistica",
    ],
    "Production / Operations / Quality": [
        "manufacturing", "production", "processing", "process", "quality", "qc",
        "qa", "mechanic", "operations", "operation", "ops", "maintenance", "winemaker", "foreman",
        "continuous improvement", "mechanics", "contract manufacturing", "distiller", "feed", "grower",
        "sustainability", "electrician", "environmental", "shop manager", "chessemaker", "chocolatier", "dairy",
        "technician", "opex", "lead formulator", "recycling", "baker", "refrigeration", "bottling", "butcher",
        "brewer", "brewery", "brewmaster", "brew\\s*house", "brewhouse", "coo", "chief operating officer",
        "director operations", "director of operations", "operations director",
        "vp operations", "vice president operations", "svp operations",
        "senior vice president operations", "head of operations",
        "operations executive", "operations supervisor", "production supervisor",
        "director quality", "director of quality", "quality director",
        "vp quality", "vice president quality", "svp quality",
        "senior vice president quality", "head of quality",
        "quality executive", "quality supervisor", "operaciones", "producción", "produccion",
    ],
    "Procurement": [
        "buyer", "buyers", "purchasing", "procurement", "sourcing", "vendor", "mro",
        "supplier", "capital projects manager", "capital project manager",
        "purchase", "purchase manager", "purchasing manager",
        "director procurement", "director of procurement", "procurement director",
        "vp procurement", "vice president procurement", "svp procurement",
        "senior vice president procurement", "head of procurement",
        "procurement executive", "procurement supervisor", "director sourcing",
        "vp sourcing", "vice president sourcing", "svp sourcing",
        "head of sourcing", "sourcing executive", "sourcing supervisor",
    ],
    "Plant Management": [
        "plant manager", "plant operations", "facilities manager",
        "facility and equipment manager", "plant management manager",
        "plant operation manager", "director facilities", "director of facilities", "facilities director",
        "vp facilities", "vice president facilities", "svp facilities",
        "senior vice president facilities", "head of facilities",
        "facilities executive", "facilities supervisor", "director plant",
        "vp plant", "vice president plant", "svp plant", "head of plant",
        "plant executive", "plant supervisor", "director plant operations",
        "vp plant operations", "vice president plant operations",
        "svp plant operations", "head of plant operations",
        "plant operations executive", "plant operations supervisor", "gerente de planta",
    ],
}

# ==========================
# Priority Categories (auto-built)
# ==========================
PRIORITY_CATEGORY_NAMES = [
    "Sales",
    "Regulatory Affairs / Validation / Compliance",
    "Procurement",
    "Production / Operations / Quality",
    "Package Design or Development / Brand Management",
]

def build_priority_categories(category_keywords: dict, priority_names: list):
    priority_list = []
    for name in priority_names:
        if name in category_keywords:
            pattern = r"\b(" + "|".join(map(re.escape, category_keywords[name])) + r")\b"
            priority_list.append((name, pattern))
    return priority_list

PRIORITY_CATEGORIES = build_priority_categories(CATEGORY_KEYWORDS, PRIORITY_CATEGORY_NAMES)

# ==========================
# Normalization helpers
# ==========================
def normalize_title(title: str) -> str:
    t = str(title).strip()
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)
    t = t.lower()
    t = re.sub(r"[-/]", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)

    t = re.sub(r"\bco[-\s]*(founder|owner)\b", r"co \1", t)
    t = re.sub(r"\bpres\b", "president", t)
    t = re.sub(r"\bpresidente\b", "president", t)
    t = re.sub(r"\bpresident(owner|founder|partner)\b", r"president \1", t)

    t = re.sub(r"\bpres(?:ident)?ceo\b", "president ceo", t)
    t = re.sub(r"\bpres(?:ident)?cfo\b", "president cfo", t)
    t = re.sub(r"\bpres(?:ident)?coo\b", "president coo", t)
    t = re.sub(r"\bpres(?:ident)?cmo\b", "president cmo", t)
    t = re.sub(r"\bpres(?:ident)?chief\b", "president chief", t)
    t = re.sub(r"\bceo(president|owner|founder)\b", r"ceo \1", t)

    t = re.sub(r"\blogistcs\b", "logistics", t)
    t = re.sub(r"\blogisitcs\b", "logistics", t)
    t = re.sub(r"\bmanger\b", "manager", t)
    t = re.sub(r"\bsr\b", "senior", t)
    t = re.sub(r"\bdir\b", "director", t)
    t = re.sub(r"\bmgr\b", "manager", t)
    t = re.sub(r"\bpkg\b", "packaging", t)
    t = re.sub(r"\beng\b", "engineer", t)
    return t

def is_executive(t: str) -> bool:
    if any(word in t for word in ASSISTANT_EXCLUSIONS):
        return False
    return any(re.search(rf"\b{re.escape(exec_title)}\b", t) for exec_title in EXEC_TITLES)

# ==========================
# Updated main classification
# ==========================
def classify_title(title: str) -> str:
    t = normalize_title(title)
    _dbg(f"Classifying: {title}")

    for pat in UNDESIRABLE_PATTERNS:
        if re.search(pat, t, flags=re.IGNORECASE):
            if "designer" in t and "packaging" in t:
                _dbg("→ Designer but includes packaging → continue")
                break
            _dbg("→ Undesirable match → Other")
            return CATEGORY_LABELS["Other"]

    for label, pattern in PRIORITY_CATEGORIES:
        if re.search(pattern, t, flags=re.IGNORECASE):
            if label in [
                "Procurement",
                "Production / Operations / Quality",
                "Package Design or Development / Brand Management",
            ]:
                for eng_word in CATEGORY_KEYWORDS["Engineering"]:
                    if re.search(rf"\b{re.escape(eng_word)}\b", t, flags=re.IGNORECASE):
                        _dbg(f"→ Engineering override for {label} → Engineering")
                        return CATEGORY_LABELS["Engineering"]

            if label == "Procurement" and re.search(r"\bpackag(e|ing)\s*design\b", t, flags=re.IGNORECASE):
                _dbg("→ Procurement title with 'package design' → Package Design/Brand Mgmt")
                return CATEGORY_LABELS["Package Design or Development / Brand Management"]

            if label == "Production / Operations / Quality" and re.search(r"\bpackag(e|ing)\s*design\b", t, flags=re.IGNORECASE):
                _dbg("→ Production / Operations / Quality title with 'package design' → Package Design/Brand Mgmt")
                return CATEGORY_LABELS["Package Design or Development / Brand Management"]

            _dbg(f"→ Priority match → {label}")
            return CATEGORY_LABELS[label]

    t = re.sub(r"\bplt\b", "plant", t)
    t = re.sub(r"\bplnt\b", "plant", t)
    if re.search(r"\bplant\b(?:\s+\w+){0,3}?\s+\b(manager|vp|director|gm|head|supervisor|superintendent)\b", t):
        return CATEGORY_LABELS["Plant Management"]

    if re.search(r"\b(program|project)\s+(manager|coordinator|lead|specialist)\b", t):
        if not re.search(
            r"\b(engineer|engineering|environmental|quality|operations?|production|manufacturing|regulatory|compliance|safety|validation|supply\s*chain|logistics|procurement|design|development|rd|r&d|branding|marketing|sustainability|maintenance|process|plant|automation|packaging|innovation)\b",
            t,
        ):
            return CATEGORY_LABELS["Other"]

    if re.search(r"\b(head|head of)\s+(design|designer|graphic|visual|web|creative|ux|ui|digital|art)\b", t):
        return CATEGORY_LABELS["Other"]

    if re.search(r"\b(global\s+head|vp[, ]*\s*head|head)(\b|[\s\-:]+)", t, flags=re.IGNORECASE):
        if re.search(r"\b(engineer|engineering)\b", t): return CATEGORY_LABELS["Engineering"]
        if re.search(r"\b(logistics|shipping|supply\s*chain|warehouse|distribution)\b", t): return CATEGORY_LABELS["Logistics / Supply Chain Management"]
        if re.search(r"\b(packaging|package design|brand|product development|r&d|innovation)\b", t): return CATEGORY_LABELS["Package Design or Development / Brand Management"]
        if re.search(r"\b(procurement|purchasing|sourcing|buyer|purchase|buying)\b", t): return CATEGORY_LABELS["Procurement"]
        if re.search(r"\b(operations?|production|manufacturing|quality|baker|brewer|brewery|environment|ecommerce)\b", t): return CATEGORY_LABELS["Production / Operations / Quality"]
        if re.search(r"\b(compliance|regulatory|safety|food safety)\b", t): return CATEGORY_LABELS["Regulatory Affairs / Validation / Compliance"]
        if re.search(r"\bsales\b", t): return CATEGORY_LABELS["Sales"]
        if re.search(r"\b(hr|human resources|people|talent|customer|consult|analyst|finance|account|legal|media|it|information technology|lab|research|client|service|experience)\b", t): return CATEGORY_LABELS["Other"]
        return CATEGORY_LABELS["CEO / General Manager / Other Senior Management"]

    for category, keywords in CATEGORY_KEYWORDS.items():
        for word in keywords:
            if re.search(rf"\b{re.escape(word)}\b", t, flags=re.IGNORECASE):
                return CATEGORY_LABELS[category]

    if is_executive(t):
        return CATEGORY_LABELS["CEO / General Manager / Other Senior Management"]

    return CATEGORY_LABELS["Other"]

# ==========================
# Value_ID mappings by Demographic_ID (brand)
# ==========================
VALUE_MAP_BY_DEMO = {
    101: {
        "Package Design or Development/Brand Management": 1055,
        "Production/Operations/Quality": 1049,
        "Engineering": 1048,
        "Plant Management": 1047,
        "CEO/General Manager/Other Senior Management": 1046,
        "Logistics/Supply Chain Management": 1053,
        "Regulatory Affairs/Validation/Compliance": 1054,
        "Procurement": 1050,
        "Sales": 1051,
        "Other": 1052,
    },
    84: {
        "Package Design or Development/Brand Management": 1029,
        "Production/Operations/Quality": 1023,
        "Engineering": 1022,
        "Plant Management": 1021,
        "CEO/General Manager/Other Senior Management": 1020,
        "Logistics/Supply Chain Management": 1027,
        "Regulatory Affairs/Validation/Compliance": 1028,
        "Procurement": 1024,
        "Sales": 1025,
        "Other": 1026,
    },
    97: {
        "Production/Operations/Quality": 1041,
        "Engineering": 1040,
        "Plant Management": 1039,
        "CEO/General Manager/Other Senior Management": 1038,
        "Logistics/Supply Chain Management": 1045,
        "Procurement": 1042,
        "Sales": 1043,
        "Other": 1044,
    },
}

def map_value_id(job_duty: str, demo_id):
    try:
        demo_id = int(demo_id)
    except (ValueError, TypeError):
        return None
    value_map = VALUE_MAP_BY_DEMO.get(demo_id, {})
    return value_map.get(job_duty, value_map.get("Other"))

# ==========================
# Processing helpers
# ==========================
def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()

    if "Customer Id" in df.columns:
        df.rename(columns={"Customer Id": "Customer_ID"}, inplace=True)
    if "group_key" not in df.columns:
        raise ValueError("Missing 'group_key' column (should contain Demographic_IDs: 84, 97, 101)")
    if "Title" not in df.columns:
        raise ValueError("Missing 'Title' column.")

    df["group_key"] = df["group_key"].astype(str).str.strip()
    df["Demographic_ID"] = df["group_key"].astype(int)

    df["Job Duties"] = df["Title"].apply(classify_title)

    def adjust_job_duty(row):
        demo_id = row["Demographic_ID"]
        job_duty = row["Job Duties"]
        value_map = VALUE_MAP_BY_DEMO.get(demo_id, {})
        if job_duty not in value_map:
            return "Other"
        return job_duty

    df["Job Duties"] = df.apply(adjust_job_duty, axis=1)
    df["Value_ID"] = df.apply(lambda x: map_value_id(x["Job Duties"], x["Demographic_ID"]), axis=1)

    output_cols = ["Customer_ID", "Title", "Job Duties", "Demographic_ID", "Value_ID"]
    return df[output_cols]

def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Processed")
    output.seek(0)
    return output.getvalue()

# ==========================
# Streamlit App
# ==========================
st.set_page_config(page_title="Job Duty Classification Processor", page_icon="📊", layout="centered")

st.title("Job Duty Classification Processor")
st.write("Upload a CSV file with at least `Title` and `group_key` columns. The app classifies job duties and returns an Excel file.")

with st.expander("Required columns and notes", expanded=False):
    st.markdown(
        """
        - Required columns:
          - `Title`
          - `group_key` (Demographic_ID values such as `84`, `97`, `101`)
        - Optional:
          - `Customer Id` (will be renamed to `Customer_ID` in the output)
        - Output:
          - Excel file with `Customer_ID`, `Title`, `Job Duties`, `Demographic_ID`, `Value_ID`
        """
    )

uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file is not None:
    st.success(f"Loaded file: {uploaded_file.name}")

    if st.button("Process file", type="primary"):
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                input_df = pd.read_csv(uploaded_file, dtype=str)
            elif uploaded_file.name.lower().endswith(".xlsx"):
                input_df = pd.read_excel(uploaded_file, dtype=str)
            else:
                raise ValueError("Unsupported file type. Please upload a CSV or XLSX file.")

            processed_df = process_dataframe(input_df)
            excel_bytes = dataframe_to_excel_bytes(processed_df)
            current_date = datetime.now().strftime("%m%d%Y")
            output_filename = f"processed_job_duties_{current_date}.xlsx"

            st.success("Processing complete.")
            st.dataframe(processed_df.head(50), use_container_width=True)

            st.download_button(
                label="Download processed Excel",
                data=excel_bytes,
                file_name=output_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as exc:
            st.error(f"Error: {exc}")
