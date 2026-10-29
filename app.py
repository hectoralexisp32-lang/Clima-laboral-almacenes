import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime

client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

MODELO = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """
Eres un consultor experto en clima laboral y retención de personal en empresas de almacenes, logística y distribución.

Tu objetivo es mantener una conversación natural y empática con el colaborador para entender:

- Ambiente de trabajo y clima laboral
- Liderazgo de supervisores y jefes de área
- Oportunidades de crecimiento
- Condiciones físicas, seguridad y reconocimiento
- Comunicación interna
- Motivos que podrían llevar a la persona a renunciar

Al final de la conversación (cuando tengas suficiente información), genera ÚNICAMENTE un JSON con este formato exacto:

{
  "nivel_satisfaccion": "bajo | medio | alto",
  "riesgo_rotacion": "bajo | medio | alto",
  "problemas_principales": ["problema 1", "problema 2", "problema 3"],
  "fortalezas": ["fortaleza 1", "fortaleza 2"],
  "recomendaciones_empresa": [
    "recomendación concreta 1",
    "recomendación concreta 2",
    "recomendación concreta 3"
  ],
  "resumen": "resumen breve y profesional de la situación"
}

Sé empático, profesional y orientado a soluciones.
"""

st.set_page_config(page_title="Clima Laboral - Almacenes", page_icon="🏭", layout="centered")
st.title("🏭 Evaluación de Clima Laboral - Almacenes")
st.caption("Evaluación anónima para detectar oportunidades de mejora y reducir la rotación de personal")

# Inicializar variables
if "evaluaciones" not in st.session_state:
    st.session_state.evaluaciones = []

if "datos_iniciales" not in st.session_state:
    st.session_state.datos_iniciales = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "analisis_final" not in st.session_state:
    st.session_state.analisis_final = None

# ========== PASO 1: Datos anónimos ==========
if st.session_state.datos_iniciales is None:
    st.subheader("Datos de la evaluación (anónimo)")

    area = st.selectbox(
        "Área de trabajo",
        ["Selecciona un área", "Picking", "Empaque", "Recibo", "Despacho", "Almacenaje", "Inventarios", "Calidad", "Otro"]
    )

    turno = st.selectbox(
        "Turno",
        ["Selecciona un turno", "Matutino", "Vespertino", "Nocturno", "Mixto"]
    )

    if st.button("Comenzar evaluación"):
        if area != "Selecciona un área" and turno != "Selecciona un turno":
            st.session_state.datos_iniciales = {
                "area": area,
                "turno": turno
            }
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"Hola 👋 Vamos a platicar sobre el ambiente de trabajo en el área de **{area}** (turno {turno}). ¿Cómo describirías el clima laboral actualmente?"
                }
            ]
            st.rerun()
        else:
            st.warning("Por favor selecciona el Área y el Turno.")

# ========== PASO 2: Conversación ==========
else:
    st.info(f"Evaluación anónima | Área: **{st.session_state.datos_iniciales['area']}** | Turno: **{st.session_state.datos_iniciales['turno']}**")

    # Mostrar historial de chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Entrada del usuario
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
                        temperature=0.7,
                    )
                    respuesta = response.choices[0].message.content
                    st.markdown(respuesta)
                except Exception as e:
                    st.error(f"Error: {e}")
                    respuesta = "Lo siento, ocurrió un problema. Intenta de nuevo."

        st.session_state.messages.append({"role": "assistant", "content": respuesta})

        # Detectar JSON
        if "{" in respuesta and "nivel_satisfaccion" in respuesta:
            try:
                inicio = respuesta.find("{")
                fin = respuesta.rfind("}") + 1
                analisis = json.loads(respuesta[inicio:fin])
                st.session_state.analisis_final = analisis

                # Guardar evaluación completa (anónima)
                evaluacion = {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "area": st.session_state.datos_iniciales["area"],
                    "turno": st.session_state.datos_iniciales["turno"],
                    "nivel_satisfaccion": analisis.get("nivel_satisfaccion", ""),
                    "riesgo_rotacion": analisis.get("riesgo_rotacion", ""),
                    "problemas_principales": " | ".join(analisis.get("problemas_principales", [])),
                    "fortalezas": " | ".join(analisis.get("fortalezas", [])),
                    "recomendaciones": " | ".join(analisis.get("recomendaciones_empresa", [])),
                    "resumen": analisis.get("resumen", "")
                }
                st.session_state.evaluaciones.append(evaluacion)

            except:
                pass

    # Mostrar resultado individual
    if st.session_state.analisis_final:
        st.divider()
        st.subheader("📊 Resultado de esta evaluación")

        a = st.session_state.analisis_final

        col1, col2 = st.columns(2)
        col1.metric("Nivel de Satisfacción", a.get("nivel_satisfaccion", "—").upper())
        col2.metric("Riesgo de Rotación", a.get("riesgo_rotacion", "—").upper())

        st.markdown("**Resumen:**")
        st.info(a.get("resumen", ""))

        if a.get("problemas_principales"):
            st.markdown("**Principales problemas detectados:**")
            for p in a["problemas_principales"]:
                st.write(f"• {p}")

        if a.get("fortalezas"):
            st.markdown("**Fortalezas identificadas:**")
            for f in a["fortalezas"]:
                st.write(f"• {f}")

        if a.get("recomendaciones_empresa"):
            st.markdown("**Recomendaciones para la empresa:**")
            for r in a["recomendaciones_empresa"]:
                st.write(f"• {r}")

    if st.button("🔄 Empezar nueva evaluación"):
        st.session_state.datos_iniciales = None
        st.session_state.messages = []
        st.session_state.analisis_final = None
        st.rerun()

# ========== DESCARGA DE DATOS ==========
st.divider()
st.subheader("📥 Descargar datos recolectados")

if st.session_state.evaluaciones:
    df = pd.DataFrame(st.session_state.evaluaciones)

    st.write(f"Se han recolectado **{len(df)}** evaluaciones anónimas.")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar CSV",
        data=csv,
        file_name=f"clima_laboral_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

    json_data = json.dumps(st.session_state.evaluaciones, ensure_ascii=False, indent=2)
    st.download_button(
        label="⬇️ Descargar JSON",
        data=json_data,
        file_name=f"clima_laboral_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json"
    )
else:
    st.info("Aún no hay evaluaciones guardadas.")

st.markdown("---")
st.caption("Evaluación 100% anónima. No se recolectan nombres ni datos personales.")

