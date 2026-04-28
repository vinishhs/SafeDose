import io
import os
import shutil

import requests
import streamlit as st
from PIL import Image

try:
    import cv2
    import numpy as np
    import pytesseract
except ImportError:
    cv2 = None
    np = None
    pytesseract = None


st.set_page_config(
    page_title="SafeDose",
    page_icon="⚕️",
    layout="wide",
)


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
    --bg-top: #0c1b2c;
    --bg-bottom: #171b3b;
    --panel: rgba(18, 29, 49, 0.94);
    --panel-soft: rgba(30, 41, 68, 0.94);
    --line: rgba(138, 161, 188, 0.22);
    --text: #e8eefc;
    --muted: #9aa8c6;
    --teal: #46e0db;
    --cyan: #32cbd0;
    --blue: #4263ff;
    --blue-soft: rgba(66, 99, 255, 0.18);
    --good: #44d6b8;
    --warn: #f0c56b;
    --bad: #ff8e91;
}

html, body, [class*="css"]  {
    font-family: "Outfit", "Bahnschrift", "Trebuchet MS", sans-serif;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 12% 18%, rgba(52, 203, 208, 0.18), transparent 28%),
        radial-gradient(circle at 88% 26%, rgba(79, 96, 255, 0.16), transparent 22%),
        linear-gradient(135deg, var(--bg-top), var(--bg-bottom));
    color: var(--text);
}

[data-testid="stHeader"] {
    background: rgba(7, 14, 27, 0.45);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

[data-testid="stToolbar"] {
    right: 1rem;
}

[data-testid="stSidebar"] {
    display: none;
}

.block-container {
    padding-top: 1.6rem;
    padding-bottom: 2.5rem;
    max-width: 1380px;
}

.app-shell {
    position: relative;
}

.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    padding: 0.15rem 0.1rem 1.1rem 0.1rem;
}

.brand {
    display: flex;
    align-items: center;
    gap: 0.9rem;
}

.brand-mark {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    color: #06141d;
    font-size: 1.25rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--teal), #78f5d6);
    box-shadow: 0 12px 32px rgba(70, 224, 219, 0.22);
}

.brand-copy h1 {
    margin: 0;
    font-size: 2rem;
    letter-spacing: -0.04em;
    line-height: 1;
    color: #6cf6e5;
}

.brand-copy p {
    margin: 0.35rem 0 0 0;
    color: var(--muted);
    font-size: 0.98rem;
}

.top-actions {
    display: flex;
    gap: 0.75rem;
}

.glass-chip {
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: var(--muted);
    background: rgba(255, 255, 255, 0.04);
    border-radius: 999px;
    padding: 0.65rem 1rem;
    font-size: 0.92rem;
}

.hero-card {
    background: linear-gradient(180deg, rgba(19, 31, 52, 0.96), rgba(22, 29, 55, 0.92));
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 34px;
    padding: 1.8rem 1.9rem 2rem 1.9rem;
    box-shadow: 0 28px 80px rgba(3, 8, 18, 0.36);
}

.hero-copy {
    margin-bottom: 1.2rem;
}

.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    background: rgba(70, 224, 219, 0.12);
    color: #7ef7ea;
    font-size: 0.86rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.hero-copy h2 {
    margin: 1rem 0 0.55rem 0;
    font-size: 3rem;
    line-height: 1.02;
    letter-spacing: -0.05em;
}

.hero-copy p {
    margin: 0;
    max-width: 760px;
    color: var(--muted);
    font-size: 1.04rem;
}

.section-card {
    background: linear-gradient(180deg, rgba(20, 30, 50, 0.84), rgba(22, 30, 56, 0.86));
    border: 1px solid var(--line);
    border-radius: 28px;
    padding: 1.35rem 1.35rem 1.15rem 1.35rem;
    min-height: 100%;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(20, 30, 50, 0.88), rgba(22, 30, 56, 0.9));
    border: 1px solid var(--line) !important;
    border-radius: 28px !important;
    padding: 0.4rem 0.55rem !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
}

.section-title {
    margin-bottom: 0.95rem;
}

.section-title h3 {
    margin: 0;
    font-size: 1.75rem;
    letter-spacing: -0.03em;
}

.section-title p {
    margin: 0.35rem 0 0 0;
    color: var(--muted);
    font-size: 0.98rem;
}

.input-label {
    color: #c9d6ef;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-size: 0.8rem;
    margin-bottom: 0.35rem;
}

.upload-hint {
    color: var(--muted);
    font-size: 0.95rem;
    margin-top: 0.35rem;
}

.result-banner {
    border-radius: 20px;
    padding: 1rem 1.1rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    margin-top: 1rem;
}

.result-safe {
    background: rgba(68, 214, 184, 0.12);
    color: #b7fff1;
}

.result-alert {
    background: rgba(255, 142, 145, 0.12);
    color: #ffd8db;
}

.mini-title {
    color: #dbe5fb;
    font-size: 1.02rem;
    margin-top: 1rem;
    margin-bottom: 0.55rem;
    letter-spacing: 0.01em;
}

.note {
    color: var(--muted);
    font-size: 0.88rem;
}

div[data-baseweb="input"] input,
div[data-baseweb="base-input"] input,
div[data-baseweb="textarea"] textarea,
textarea,
input {
    background: rgba(255, 255, 255, 0.06) !important;
    color: var(--text) !important;
    border-radius: 18px !important;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] > div,
div[data-baseweb="textarea"] > div {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(178, 193, 223, 0.16) !important;
    border-radius: 18px !important;
    box-shadow: none !important;
}

div[data-baseweb="select"] span,
label,
.stMarkdown,
p,
li {
    color: var(--text);
}

div[role="radiogroup"] {
    display: flex;
    gap: 0.7rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.35rem;
    width: fit-content;
}

div[role="radiogroup"] label {
    background: transparent !important;
    border-radius: 999px !important;
    padding: 0.35rem 0.95rem !important;
}

div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(135deg, rgba(70, 224, 219, 0.28), rgba(66, 99, 255, 0.32)) !important;
    border: 1px solid rgba(126, 247, 234, 0.15);
}

.stButton > button {
    width: 100%;
    min-height: 3.35rem;
    border-radius: 18px;
    border: 1px solid rgba(120, 140, 255, 0.18);
    background: linear-gradient(90deg, var(--cyan), var(--blue));
    color: #08111a;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    box-shadow: 0 20px 40px rgba(52, 100, 255, 0.28);
}

.stButton > button:hover {
    border-color: rgba(126, 247, 234, 0.35);
    color: #041015;
}

[data-testid="stFileUploader"] {
    background: linear-gradient(180deg, rgba(23, 33, 58, 0.88), rgba(25, 32, 59, 0.82));
    border: 2px dashed rgba(164, 180, 206, 0.26);
    border-radius: 26px;
    padding: 1rem;
}

[data-testid="stFileUploader"] section {
    padding: 1.35rem 0.8rem;
}

[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] label {
    color: var(--muted) !important;
}

[data-testid="stImage"] img {
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

[data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlockBorderWrapper"] {
    width: 100%;
}

.footer-note {
    text-align: center;
    color: var(--muted);
    font-size: 0.88rem;
    margin-top: 1.4rem;
}

@media (max-width: 900px) {
    .hero-copy h2 {
        font-size: 2.2rem;
    }

    .brand-copy h1 {
        font-size: 1.6rem;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


def ocr_available():
    return all(module is not None for module in (cv2, np, pytesseract))


def configure_tesseract():
    if pytesseract is None:
        return

    discovered_path = shutil.which("tesseract")
    fallback_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    tesseract_path = discovered_path or (fallback_path if os.path.exists(fallback_path) else None)
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


configure_tesseract()


def preprocess_image_for_ocr(image):
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    denoised = cv2.fastNlMeansDenoising(gray)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((1, 1), np.uint8)
    return cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)


def extract_text_from_image(image):
    if not ocr_available():
        return "", "OCR dependencies are not installed in this environment."

    try:
        processed_image = preprocess_image_for_ocr(image)
        custom_config = (
            r"--oem 3 --psm 6 "
            r"-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            r"abcdefghijklmnopqrstuvwxyz0123456789.,()/-: "
        )
        extracted_text = pytesseract.image_to_string(processed_image, config=custom_config)
        return extracted_text.strip(), None
    except Exception as e:
        return "", f"Local OCR failed: {str(e)}"


def extract_text_from_image_api(uploaded_file):
    api_url = "http://localhost:8000/extract-text"

    try:
        response = requests.post(
            api_url,
            files={
                "image_file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    uploaded_file.type or "application/octet-stream",
                )
            },
            timeout=60,
        )
        if response.status_code == 200:
            payload = response.json()
            if payload.get("success"):
                return payload.get("extracted_text", ""), None
            return "", payload.get("error", "OCR failed")
        return "", f"API Error: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return "", f"Connection failed: {str(e)}"


def parse_list_field(value, negative_values):
    cleaned = (value or "").strip()
    if not cleaned or cleaned.lower() in negative_values:
        return []
    return [item.strip() for item in cleaned.split(",") if item.strip()]


def analyze_prescription_api(text, patient_context):
    api_url = "http://localhost:8000/verify"
    payload = {
        "patient": patient_context,
        "drugs": [],
        "text_input": text,
    }

    try:
        response = requests.post(api_url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json(), None
        return None, f"API Error: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return None, f"Connection failed: {str(e)}"


if "ocr_text" not in st.session_state:
    st.session_state["ocr_text"] = ""

if "ocr_error" not in st.session_state:
    st.session_state["ocr_error"] = None


st.markdown(
    """
<div class="app-shell">
    <div class="topbar">
        <div class="brand">
            <div class="brand-mark">✚</div>
            <div class="brand-copy">
                <h1>SafeDose</h1>
                <p>Prescription intelligence with patient-aware safety checks.</p>
            </div>
        </div>
        
    
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero-card">
    <div class="hero-copy">
        <div class="eyebrow">Clinical Decision Support</div>
        <h2>Analyze prescriptions with richer patient context.</h2>
        <p>
            Upload a prescription image or enter text manually, then review extracted drugs,
            dosage considerations, interactions, and alternatives in one place.
        </p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1.05, 0.95], gap="large")

with left_col:
    with st.container(border=True):
        st.markdown(
            """
<div class="section-card">
    <div class="section-title">
        <h3>Patient Context</h3>
        <p>Provide clinical background for more grounded analysis.</p>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        age = st.number_input(
            "Age",
            min_value=0,
            max_value=120,
            value=30,
            step=1,
            
        )
        gender = st.selectbox(
            "Gender",
            options=["male", "female", "other"],
            index=0,
        )
        medical_conditions = st.text_input(
            "Any medical condition",
            value="Nil",
            help="Use comma-separated values if there are multiple conditions.",
        )
        allergies = st.text_input(
            "Allergies to medications",
            value="No",
            help="Use comma-separated values for multiple allergies.",
        )
        current_medications = st.text_input(
            "Consuming any medication now",
            value="No",
            help="List ongoing medications separated by commas when applicable.",
        )

with right_col:
    with st.container(border=True):
        st.markdown(
            """
<div class="section-card">
    <div class="section-title">
        <h3>Prescription Source</h3>
        <p>Choose image upload or manual input to drive OCR and analysis.</p>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        input_method = st.radio(
            "Prescription Source",
            ["Upload", "Manual"],
            horizontal=True,
            label_visibility="collapsed",
        )

        prescription_text = ""
        uploaded_file = None

        if input_method == "Upload":
            st.markdown(
                '<div class="upload-hint">Upload JPG, PNG, BMP, TIFF, or HEIC images for OCR extraction.</div>',
                unsafe_allow_html=True,
            )
            uploaded_file = st.file_uploader(
                "Upload prescription image",
                type=["png", "jpg", "jpeg", "bmp", "tiff", "heic"],
                label_visibility="collapsed",
            )

            if uploaded_file is not None:
                image = Image.open(io.BytesIO(uploaded_file.getvalue()))
                st.image(image, caption="Prescription preview", use_container_width=True)

                if st.button("Extract Text From Image", key="extract_text_button"):
                    with st.spinner("Running OCR on the uploaded image..."):
                        extracted_text, api_error = extract_text_from_image_api(uploaded_file)
                        if not extracted_text:
                            local_text, local_error = extract_text_from_image(image)
                            extracted_text = local_text
                            api_error = api_error or local_error

                        st.session_state["ocr_text"] = extracted_text
                        st.session_state["ocr_error"] = api_error if not extracted_text else None

                if st.session_state["ocr_text"]:
                    st.text_area(
                        "Extracted text",
                        value=st.session_state["ocr_text"],
                        height=220,
                        key="ocr_text_editor",
                        help="You can edit the OCR output before analysis.",
                    )
                    prescription_text = st.session_state.get("ocr_text_editor", st.session_state["ocr_text"])

                if st.session_state["ocr_error"]:
                    st.error(st.session_state["ocr_error"])
        else:
            prescription_text = st.text_area(
                "Manual prescription text",
                value=st.session_state.get("ocr_text", ""),
                height=310,
                placeholder="Paste or type the prescription text here...",
            )


patient_context = {
    "age": int(age),
    "gender": gender,
    "conditions": parse_list_field(medical_conditions, {"nil", "none", "no", "n/a"}),
    "allergies": parse_list_field(allergies, {"nil", "none", "no", "n/a"}),
    "current_medications": parse_list_field(current_medications, {"nil", "none", "no", "n/a"}),
}

st.markdown('<div style="height: 1.1rem;"></div>', unsafe_allow_html=True)

if st.button("Analyze Prescription", key="analyze_button", use_container_width=True):
    source_text = prescription_text.strip()
    if not source_text:
        st.error("Provide prescription text directly or extract it from an uploaded image before analysis.")
    else:
        with st.spinner("Reviewing prescription safety and dosage guidance..."):
            result, error = analyze_prescription_api(source_text, patient_context)
            st.session_state["analysis_result"] = result
            st.session_state["analysis_error"] = error


if st.session_state.get("analysis_error"):
    st.error(st.session_state["analysis_error"])
    st.info("Make sure the backend API is running on http://localhost:8000")


result = st.session_state.get("analysis_result")
if result:
    is_safe = result.get("is_safe", False)
    banner_class = "result-safe" if is_safe else "result-alert"
    banner_title = "Prescription appears clear for the current rule set." if is_safe else "Prescription needs attention before use."
    banner_body = (
        "No interaction or dosage conflicts were returned by the current checks."
        if is_safe
        else "One or more interactions, dosage advisories, or substitution hints were returned."
    )

    st.markdown(
        f"""
<div class="result-banner {banner_class}">
    <strong>{banner_title}</strong><br>
    <span>{banner_body}</span>
</div>
""",
        unsafe_allow_html=True,
    )

    result_col1, result_col2 = st.columns(2, gap="large")

    with result_col1:
        st.markdown('<div class="mini-title">Extracted Drugs</div>', unsafe_allow_html=True)
        extracted_drugs = result.get("extracted_drugs", [])
        if extracted_drugs:
            for drug in extracted_drugs:
                drug_name = drug.get("name", "Unknown Drug")
                dosage = drug.get("dosage") or "Dosage not detected"
                frequency = drug.get("frequency") or "Frequency not detected"
                st.markdown(f"**{drug_name}**")
                st.caption(f"{dosage} • {frequency}")
        else:
            st.caption("No drugs were extracted from the submitted text.")

        st.markdown('<div class="mini-title">Dosage Guidance</div>', unsafe_allow_html=True)
        dosage_alerts = result.get("dosage_alerts", [])
        if dosage_alerts:
            for alert in dosage_alerts:
                line = alert.get("issue", "Dosage guidance available")
                if alert.get("recommended_dosage"):
                    line = f"{line} Recommended: {alert['recommended_dosage']}"
                st.info(f"{alert.get('drug', 'Unknown Drug')}: {line}")
        else:
            st.caption("No dosage advisories were returned.")

    with result_col2:
        st.markdown('<div class="mini-title">Interaction Signals</div>', unsafe_allow_html=True)
        interactions = result.get("interactions", [])
        if interactions:
            for interaction in interactions:
                st.warning(
                    f"{interaction.get('drug_a', 'Drug A')} + {interaction.get('drug_b', 'Drug B')}: "
                    f"{interaction.get('description', 'Potential interaction')}"
                )
        else:
            st.success("No known interactions found in the current rules.")

        st.markdown('<div class="mini-title">Alternative Suggestions</div>', unsafe_allow_html=True)
        alternatives = result.get("alternatives", [])
        if alternatives:
            for suggestion in alternatives:
                st.markdown(
                    f"**{suggestion.get('original_drug', 'Unknown')}** → "
                    f"**{suggestion.get('suggested_drug', 'N/A')}**"
                )
                st.caption(suggestion.get("reason", ""))
        else:
            st.caption("No alternative suggestions were generated.")


st.markdown(
    """
<div class="footer-note">
    Educational support only. Clinical decisions should still be confirmed by a licensed healthcare professional.
</div>
""",
    unsafe_allow_html=True,
)
