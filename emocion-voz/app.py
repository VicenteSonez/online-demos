"""Mini-demo: emoción en la voz (resultado preliminar).  Uso:  streamlit run app.py"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

AQUI = Path(__file__).resolve().parent
AUDIO = next((p for p in (AQUI / "data").glob("audio_ejemplo.*") if p.suffix in {".wav", ".mp3", ".ogg"}), None)

ES = {"alegria": "alegría"}
# sin "neutral": las gráficas muestran solo las demás emociones
EMOCIONES = ["alegria", "tristeza", "enojo", "miedo", "asco", "sorpresa", "otra", "desconocida"]
COLORES = ["#f2c14e", "#4f8fd6", "#d1495b", "#9b6bd1", "#6a994e", "#ee964b", "#5b6270", "#3d4350"]
EN = {"alegria": "s_happy", "tristeza": "s_sad"}   # clases no neutrales que aparecen en el extracto
DOMINIO = [ES.get(e, e) for e in EMOCIONES]

st.set_page_config(page_title="Emoción en la voz", layout="wide")


@st.cache_data
def cargar():
    curva = pd.read_csv(AQUI / "data" / "curva_ejemplo.csv")
    resumen = pd.read_csv(AQUI / "data" / "resumen_preguntas.csv", dtype={"sesion": str})
    return curva, resumen


curva, resumen = cargar()
color = alt.Color("emocion:N", title=None, scale=alt.Scale(domain=DOMINIO, range=COLORES),
                  legend=alt.Legend(orient="top"))

st.caption("Resultado preliminar, sin validar con etiquetas humanas.")

if AUDIO is not None:
    st.audio(str(AUDIO))

# --- Curva del extracto ---
largo = curva.melt(id_vars="t_centro_s", value_vars=list(EN.values()), var_name="clase", value_name="prob")
largo["emocion"] = largo["clase"].map({v: ES.get(k, k) for k, v in EN.items()})
st.altair_chart(
    alt.Chart(largo).mark_line(strokeWidth=3).encode(
        x=alt.X("t_centro_s:Q", title="Segundos"),
        y=alt.Y("prob:Q", title="Probabilidad", scale=alt.Scale(domain=[0, 1])),
        color=color,
        tooltip=["emocion", alt.Tooltip("t_centro_s:Q", title="s"), alt.Tooltip("prob:Q", format=".0%")],
    ).properties(height=320),
    use_container_width=True,
)

# --- % de ventanas por emoción, sin contar las ventanas neutral ---
largo_r = resumen.melt(id_vars=["sesion", "pregunta", "n_ventanas"], value_vars=[f"pct_{e}" for e in EMOCIONES],
                       var_name="emocion", value_name="pct")
largo_r["emocion"] = largo_r["emocion"].str.removeprefix("pct_").replace(ES)
largo_r["ventanas"] = largo_r["pct"] * largo_r["n_ventanas"]
largo_r["orden"] = largo_r["emocion"].map({e: i for i, e in enumerate(DOMINIO)})

c1, c2 = st.columns(2)
nivel = c1.radio("Ver por", ["Sesión", "Pregunta"], horizontal=True, label_visibility="collapsed")
if nivel == "Sesión":
    datos = largo_r.groupby(["sesion", "emocion", "orden"], as_index=False)["ventanas"].sum()
    clave, x, titulo_x = ["sesion"], "sesion:N", "Sesión"
else:
    sesion = c2.selectbox("Sesión", sorted(resumen["sesion"].unique()), index=2, label_visibility="collapsed")
    datos = largo_r[largo_r["sesion"] == sesion].copy()
    datos["pregunta"] = datos["pregunta"].astype(str)
    clave, x, titulo_x = ["pregunta"], "pregunta:N", f"Pregunta (sesión {sesion})"
datos["no_neutral"] = datos.groupby(clave)["ventanas"].transform("sum")   # base del 100 %

st.altair_chart(
    alt.Chart(datos).mark_bar().encode(
        x=alt.X(x, title=titulo_x, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("ventanas:Q", stack="normalize", title="% de ventanas no neutrales", axis=alt.Axis(format="%")),
        color=color,
        order=alt.Order("orden:Q"),
        tooltip=["emocion", alt.Tooltip("ventanas:Q", format=".0f", title="ventanas"),
                 alt.Tooltip("no_neutral:Q", format=".0f", title="total no neutrales")],
    ).properties(height=320),
    use_container_width=True,
)
