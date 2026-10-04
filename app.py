from io import BytesIO
import hmac
import os

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="TalentPay · Referencias salariales", page_icon="💼", layout="wide")

st.markdown("""
<style>
.stApp {background: #f5f7fb;}
.block-container {max-width: 1280px; padding-top: 2rem;}
[data-testid="stSidebar"] {background: #eaf0f7;}
.hero {background: linear-gradient(115deg,#142b48,#285b7a); color:white; padding:30px 34px; border-radius:20px; margin-bottom:24px;}
.hero h1 {color:white; font-size:2.3rem; margin:0 0 8px;}
.hero p {color:#dce7f3; margin:0; font-size:1rem;}
.eyebrow {font-size:.78rem; letter-spacing:2px; color:#b5dbea; margin-bottom:10px;}
[data-testid="stMetric"] {background:white; padding:20px; border-radius:15px; border:1px solid #e0e7f0; box-shadow:0 4px 14px #142b4808;}
div.stButton > button[kind="primary"] {background:#176b80; border:0; border-radius:10px;}
</style>
""", unsafe_allow_html=True)


def access_control():
    """Shared password is a prototype gate, not enterprise authentication."""
    try:
        password = st.secrets.get("APP_PASSWORD", "")
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        password = ""
    password = password or os.environ.get("APP_PASSWORD", "")
    if not password:
        st.sidebar.caption("Modo demostración · Sin contraseña configurada")
        return
    if st.session_state.get("authenticated"):
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.clear()
            st.rerun()
        return
    st.title("Acceso a TalentPay")
    with st.form("login"):
        entered = st.text_input("Contraseña de acceso", type="password")
        submitted = st.form_submit_button("Entrar", type="primary")
    if submitted:
        if hmac.compare_digest(entered.encode(), str(password).encode()):
            st.session_state.authenticated = True
            st.rerun()
        st.error("Contraseña incorrecta.")
    st.stop()


def normalize(series):
    return series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True).str.casefold()


def validate(df, kind):
    columns = {
        "headcount": ["ID_Empleado", "Puesto", "Provincia", "Nivel de experiencia", "Salario bruto anual"],
        "convenios": ["Provincia", "Categoría profesional", "Salario convenio bruto anual"],
    }[kind]
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError("Faltan columnas: " + ", ".join(missing) + ". Selecciona la hoja correcta o revisa el Excel.")
    # The sample files include explanatory cells outside the data table.
    df = df[columns].dropna(how="all").copy()
    initial = len(df)
    salary = columns[-1]
    df[salary] = pd.to_numeric(df[salary], errors="coerce")
    valid = df[salary].notna() & df[salary].gt(0) & df[salary].lt(float("inf"))
    for c in columns[:-1]:
        df[c] = df[c].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        valid &= df[c].notna() & df[c].ne("")
    if kind == "headcount":
        mapping = {"junior": "Junior", "intermedio": "Intermedio", "senior": "Sénior", "sénior": "Sénior"}
        df["Nivel de experiencia"] = normalize(df["Nivel de experiencia"]).map(mapping)
        valid &= df["Nivel de experiencia"].notna()
    df = df.loc[valid].copy()
    if kind == "headcount":
        # Exclude all occurrences of duplicated employee IDs to avoid choosing an arbitrary salary.
        duplicate = normalize(df["ID_Empleado"]).duplicated(keep=False)
        df = df.loc[~duplicate].copy()
    else:
        df["_category"] = normalize(df["Categoría profesional"])
        df["_province"] = normalize(df["Provincia"])
        conflicts = df.groupby(["_province", "_category"])[salary].nunique()
        conflict_keys = set(conflicts[conflicts > 1].index)
        if conflict_keys:
            raise ValueError("Hay importes contradictorios para una misma provincia y categoría. Corrige el archivo de convenios.")
        df = df.drop_duplicates(["_province", "_category"])
    df["_province"] = normalize(df["Provincia"])
    if kind == "headcount":
        df["_role"] = normalize(df["Puesto"])
    return df, initial - len(df)


def load_excel(label, kind):
    upload = st.sidebar.file_uploader(label, type=["xlsx"], key=kind)
    if upload is None:
        return None
    try:
        data = upload.getvalue()
        book = pd.ExcelFile(BytesIO(data), engine="openpyxl")
        sheet = st.sidebar.selectbox("Hoja de " + label.lower(), book.sheet_names, key=kind + "_sheet")
        df, discarded = validate(pd.read_excel(book, sheet_name=sheet), kind)
        st.sidebar.success(f"{len(df):,} registros cargados".replace(",", "."))
        if discarded:
            st.sidebar.warning(f"{discarded} registros descartados por datos inválidos o duplicados.")
        return df
    except Exception as exc:
        st.sidebar.error(f"No se puede cargar {label.lower()}: {exc}")
        return None


def euro(value):
    return f"{value:,.0f} €".replace(",", ".")


def make_export(selection, summary, agreements):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([selection]).to_excel(writer, sheet_name="Consulta", index=False)
        pd.DataFrame([summary]).to_excel(writer, sheet_name="Referencia interna", index=False)
        agreements.to_excel(writer, sheet_name="Convenio provincial", index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for cells in sheet.columns:
                width = min(48, max(len(str(cell.value or "")) for cell in cells) + 3)
                sheet.column_dimensions[cells[0].column_letter].width = width
    return buffer.getvalue()


def main():
    access_control()
    st.sidebar.title("💼 TalentPay")
    st.sidebar.caption("Fuentes de información")
    demo = st.sidebar.toggle("Los archivos contienen datos ficticios", value=True)
    if not demo and not st.session_state.get("authenticated"):
        st.warning("Configura APP_PASSWORD en Secrets antes de trabajar con información real. Para producción, utiliza acceso corporativo y alojamiento aprobado por la empresa.")
        st.stop()
    hc = load_excel("Headcount", "headcount")
    cv = load_excel("Salarios de convenio", "convenios")
    if st.sidebar.button("Actualizar datos", use_container_width=True):
        st.session_state.pop("query", None)
        st.rerun()
    st.sidebar.caption("Se consulta la última versión cargada. Para incorporar cambios del Excel original, vuelve a cargar el archivo.")
    st.markdown('<div class="hero"><div class="eyebrow">PEOPLE ANALYTICS · CONSTRUCCIÓN</div><h1>Asistente de bandas salariales</h1><p>Referencias internas y salarios de convenio para preparar tu próxima oferta.</p></div>', unsafe_allow_html=True)
    if demo:
        st.info("🧪 Demostración académica: los salarios y las categorías de convenio son simulados; no representan tablas oficiales.")
    if hc is None or cv is None:
        st.subheader("Empieza con tus dos archivos")
        st.write("Carga el headcount y el Excel de salarios de convenio en el panel lateral. Después podrás consultar una referencia para la vacante.")
        with st.expander("¿Qué columnas deben contener?"):
            st.write("**Headcount:** ID_Empleado, Puesto, Provincia, Nivel de experiencia, Salario bruto anual.")
            st.write("**Convenios:** Provincia, Categoría profesional, Salario convenio bruto anual.")
            st.caption("Salarios en euros brutos anuales, a jornada completa. El importe de convenio ya incluye todos sus conceptos.")
        return
    if hc.empty:
        st.error("El headcount no contiene empleados válidos.")
        return
    st.subheader("Define el perfil de la vacante")
    with st.form("vacancy"):
        a, b, c = st.columns([1, 1.6, 1])
        province = a.selectbox("Provincia", sorted(hc["Provincia"].unique()))
        role = b.selectbox("Puesto", sorted(hc["Puesto"].unique()))
        level = c.selectbox("Perfil profesional", ["Junior", "Intermedio", "Sénior"])
        st.caption("Junior: menos de 3 años · Intermedio: de 3 a menos de 6 · Sénior: 6 o más años de experiencia relevante.")
        if st.form_submit_button("Consultar referencia salarial", type="primary", use_container_width=True):
            st.session_state.query = (province, role, level)
    query = st.session_state.get("query")
    if not query:
        return
    province, role, level = query
    st.caption(f"Consulta activa: {role} · {province} · {level}")
    peers = hc[(hc["_role"] == role.casefold()) & (hc["Nivel de experiencia"] == level)]
    local = peers[peers["_province"] == province.casefold()]
    scope = province
    comparable = local
    if len(local) < 5:
        st.warning(f"Solo hay {len(local)} empleados comparables en {province}. Se necesitan al menos cinco para mostrar estadísticas.")
        if st.checkbox("Ampliar al mismo puesto y perfil en todas las provincias", key="national_" + "|".join(query)):
            comparable = peers
            scope = "Todas las provincias"
    summary = {"Ámbito": scope, "Número de comparables": len(comparable)}
    if len(comparable) >= 5:
        st.subheader("Referencia salarial interna")
        salaries = comparable["Salario bruto anual"]
        stats = {"Mínimo": salaries.min(), "Máximo": salaries.max(), "Media": salaries.mean(), "Mediana": salaries.median()}
        for column, (label, value) in zip(st.columns(4), stats.items()):
            column.metric(label, euro(value))
        summary.update(stats)
        st.caption(f"{len(comparable)} empleados comparables · Ámbito: {scope} · Euros brutos anuales a jornada completa")
        st.write(f"La referencia observada para este perfil va de **{euro(stats['Mínimo'])}** a **{euro(stats['Máximo'])}**, con una mediana de **{euro(stats['Mediana'])}**. Es una orientación interna para apoyar la decisión de RR. HH.")
        # Only aggregated salary bins are passed to the chart.
        cuts = pd.cut(salaries, bins=5, duplicates="drop")
        counts = cuts.value_counts(sort=False)
        chart_data = pd.DataFrame({"Tramo salarial": [f"{euro(i.left)} – {euro(i.right)}" for i in counts.index], "Empleados": counts.values})
        fig = px.bar(chart_data, x="Tramo salarial", y="Empleados", title="Distribución del grupo comparable", color_discrete_sequence=["#217b90"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, margin=dict(l=10,r=10,t=50,b=10), yaxis=dict(dtick=1))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    elif scope == "Todas las provincias":
        st.warning("Tampoco hay suficientes comparables en el conjunto de provincias. No se calcula una banda.")
    st.divider()
    st.subheader(f"Categorías y salarios de convenio · {province}")
    agreements = cv.loc[cv["_province"] == province.casefold(), ["Categoría profesional", "Salario convenio bruto anual"]].sort_values("Salario convenio bruto anual", ascending=False)
    if agreements.empty:
        st.warning("No hay categorías de convenio disponibles para esta provincia.")
    else:
        st.dataframe(agreements, hide_index=True, use_container_width=True, column_config={"Salario convenio bruto anual": st.column_config.NumberColumn("Salario bruto anual de convenio (€)", format="%.0f €")})
        st.caption("Importe total con todos los conceptos incluidos. La categoría se determina por las funciones y responsabilidades del puesto; el nivel de experiencia no asigna una categoría automáticamente.")
        with st.expander("Comprobar una oferta salarial", expanded=False):
            with st.form("offer"):
                category = st.selectbox("Categoría profesional", agreements["Categoría profesional"].tolist())
                offered = st.number_input("Salario bruto anual propuesto (€)", min_value=0.0, value=30000.0, step=500.0)
                same_base = st.checkbox("Confirmo que ambos importes son comparables y corresponden a jornada completa")
                check = st.form_submit_button("Comprobar importe")
            if check:
                if not same_base:
                    st.warning("Confirma la misma base de comparación antes de continuar.")
                else:
                    floor = float(agreements.loc[agreements["Categoría profesional"] == category, "Salario convenio bruto anual"].iloc[0])
                    if offered < floor:
                        st.error(f"La oferta está {euro(floor-offered)} por debajo del importe registrado ({euro(floor)}).")
                    else:
                        st.success(f"La oferta alcanza el importe registrado de {euro(floor)} para esta categoría.")
                    st.caption("Comprobación del archivo proporcionado; no sustituye la revisión de Administración o Relaciones Laborales.")
    selection = {"Provincia": province, "Puesto": role, "Perfil": level, "Datos ficticios": "Sí" if demo else "No", "Base": "Euros brutos anuales, jornada completa"}
    st.download_button("↓ Descargar resumen en Excel", make_export(selection, summary, agreements), file_name="consulta_salarial.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    st.caption("TalentPay · Herramienta de apoyo a RR. HH. · Resultados agregados")


if __name__ == "__main__":
    main()
