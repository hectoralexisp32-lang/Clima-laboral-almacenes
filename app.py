import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

MODELO = "lopenai/gpt-oss-120b”

SYSTEM_PROMPT = """
Eres un consultor experto en clima laboral de almacenes y centros de distribución.

Mantén una conversación natural y empática. Pregunta sobre:
- Ambiente de trabajo
- Liderazgo de supervisores
- Oportunidades de crecimiento
- Condiciones físicas y seguridad
- Comunicación y reconocimiento

Cuando tengas suficiente información, responde ÚNICAMENTE con este JSON (sin texto adicional):

{
  "ambiente_laboral": "malo | regular | bueno",
  "liderazgo": "malo | regular | bueno",
  "oportunidades_crecimiento": "malo | regular | bueno",
  "condiciones_seguridad": "malo | regular | bueno",
  "comunicacion_reconocimiento": "malo | regular | bueno",
  "riesgo_rotacion": "bajo | medio | alto",
  "problemas_principales": ["problema 1", "problema 2"],
  "recomendaciones": ["recomendación 1", "recomendación 2", "recomendación 3"],
  "resumen": "resumen breve y profesional"
}

Sé claro, objetivo y orientado a mejorar el ambiente laboral.
"""

st.set_page_config(page_title="Clima Laboral - Almacenes", page_icon="🏭", layout="centered")
st.title("🏭 Evaluación de Clima Laboral - Almacenes")
st.caption("Evaluación anónima por área y turno")

# Inicializar
if "evaluaciones" not in st.session_state:
    st.session_state.evaluaciones = []

if "datos_iniciales" not in st.session_state:
    st.session_state.datos_iniciales = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "analisis_final" not in st.session_state:
    st.session_state.analisis_final = None

# ========== Datos anónimos ==========
if st.session_state.datos_iniciales is None:
    st.subheader("Datos de la evaluación (anónimo)")

    area = st.selectbox(
        "Área de trabajo",
        ["Selecciona un área", "PTL", "Embarques", "Resivo", "LI", "Pull", "Inventarios", "Calidad", "Otro"]
    )

    turno = st.selectbox(
        "Turno",
        ["Selecciona un turno", "Matutino", "Vespertino", "Nocturno", "Mixto"]
    )

    if st.button("Comenzar evaluación"):
        if area != "Selecciona un área" and turno != "Selecciona un turno":
            st.session_state.datos_iniciales = {"area": area, "turno": turno}
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"Hola 👋 Vamos a platicar sobre el ambiente de trabajo en el área de **{area}** (turno {turno}). ¿Cómo describirías el clima laboral actualmente?"
                }
            ]
            st.rerun()
        else:
            st.warning("Por favor selecciona el Área y el Turno.")

# ========== Conversación ==========
else:
    st.info(f"Área: **{st.session_state.datos_iniciales['area']}** | Turno: **{st.session_state.datos_iniciales['turno']}**")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Cuéntame tu experiencia..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analizando..."):
                try:
                    response = client.chat.completions.create(
                        model=MODELO,
                        messages=[{"role": "system", "content": SYSTEM_PROMPT}] +
                                 [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                        temperature=0.6,
                    )
                    respuesta = response.choices[0].message.content
                    st.markdown(respuesta)
                except Exception as e:
                    st.error(f"Error: {e}")
                    respuesta = "Lo siento, ocurrió un problema. Intenta de nuevo."

        st.session_state.messages.append({"role": "assistant", "content": respuesta})

        if "{" in respuesta and "ambiente_laboral" in respuesta:
            try:
                inicio = respuesta.find("{")
                fin = respuesta.rfind("}") + 1
                analisis = json.loads(respuesta[inicio:fin])
                st.session_state.analisis_final = analisis

                evaluacion = {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "area": st.session_state.datos_iniciales["area"],
                    "turno": st.session_state.datos_iniciales["turno"],
                    "ambiente_laboral": analisis.get("ambiente_laboral", ""),
                    "liderazgo": analisis.get("liderazgo", ""),
                    "oportunidades_crecimiento": analisis.get("oportunidades_crecimiento", ""),
                    "condiciones_seguridad": analisis.get("condiciones_seguridad", ""),
                    "comunicacion_reconocimiento": analisis.get("comunicacion_reconocimiento", ""),
                    "riesgo_rotacion": analisis.get("riesgo_rotacion", ""),
                    "problemas_principales": " | ".join(analisis.get("problemas_principales", [])),
                    "recomendaciones": " | ".join(analisis.get("recomendaciones", [])),
                    "resumen": analisis.get("resumen", "")
                }
                st.session_state.evaluaciones.append(evaluacion)
            except:
                pass

    # ========== Resultado desglosado ==========
    if st.session_state.analisis_final:
        st.divider()
        st.subheader("📊 Resultado desglosado")

        a = st.session_state.analisis_final

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Ambiente laboral", a.get("ambiente_laboral", "—").upper())
            st.metric("Liderazgo", a.get("liderazgo", "—").upper())
            st.metric("Oportunidades de crecimiento", a.get("oportunidades_crecimiento", "—").upper())

        with col2:
            st.metric("Condiciones y seguridad", a.get("condiciones_seguridad", "—").upper())
            st.metric("Comunicación y reconocimiento", a.get("comunicacion_reconocimiento", "—").upper())
            st.metric("Riesgo de rotación", a.get("riesgo_rotacion", "—").upper())

        st.markdown("**Resumen:**")
        st.info(a.get("resumen", ""))

        if a.get("problemas_principales"):
            st.markdown("**Problemas principales:**")
            for p in a["problemas_principales"]:
                st.write(f"• {p}")

        if a.get("recomendaciones"):
            st.markdown("**Recomendaciones para la empresa:**")
            for r in a["recomendaciones"]:
                st.write(f"• {r}")

    if st.button("🔄 Empezar nueva evaluación"):
        st.session_state.datos_iniciales = None
        st.session_state.messages = []
        st.session_state.analisis_final = None
        st.rerun()

# ========== Descarga ==========
st.divider()
st.subheader("📥 Descargar datos")

if st.session_state.evaluaciones:
    df = pd.DataFrame(st.session_state.evaluaciones)
    st.write(f"**{len(df)}** evaluaciones recolectadas")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar CSV",
        data=csv,
        file_name=f"clima_laboral_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
else:
    st.info("Aún no hay evaluaciones guardadas.")

st.markdown("---")
st.caption("Evaluación 100% anónima. No se recolectan datos personales.")

