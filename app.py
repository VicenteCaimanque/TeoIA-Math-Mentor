import streamlit as st
from openai import OpenAI
import pypdf
import docx
import json
import numpy as np 
import matplotlib.pyplot as plt 
import re  # Importamos expresiones regulares para la limpieza profunda
from utils.prompts import obtener_prompt, PROMPT_QUIZ_GENERATOR

# --- FUNCIÓN DE LIMPIEZA AVANZADA (SANITIZADOR) ---
def sanitizar_json_latex(data):
    """
    Recorre el JSON recursivamente y convierte los marcadores @@ y 
    las barras dobles en formato LaTeX válido para Streamlit.
    """
    if isinstance(data, str):
        # 1. Si la IA olvidó los signos $, intentamos detectarlo (heurística básica)
        # Si parece una fórmula (tiene frac, sqrt) y no tiene $, se los ponemos.
        if "frac" in data or "sqrt" in data or "^" in data:
            if "$" not in data: 
                data = f"${data}$"
        
        # 2. Reemplazo maestro: @@ -> \
        clean_text = data.replace("@@", "\\")
        
        # 3. Corrección de errores comunes de visualización
        # A veces queda \\frac (doble barra), Streamlit prefiere \frac (simple)
        clean_text = clean_text.replace("\\\\", "\\") 
        
        return clean_text
        
    elif isinstance(data, list):
        return [sanitizar_json_latex(item) for item in data]
    elif isinstance(data, dict):
        return {k: sanitizar_json_latex(v) for k, v in data.items()}
    return data

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Teo - Tu Profe IA", page_icon="🐼", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 3rem;}
    .stRadio p {font-size: 16px;}
</style>
""", unsafe_allow_html=True)

# --- CLAVE API ---
CLAVE_OPENAI = "TU_API_KEY_AQUI"

try:
    client = OpenAI(api_key=CLAVE_OPENAI)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- 2. BARRA LATERAL ---
with st.sidebar:
    st.image("logo_panda.png", width=180)
    modo_seleccionado = st.selectbox("Personalidad", ["Profesor de Primaria", "Profesor de Secundaria"])
    PROMPT_SISTEMA = obtener_prompt(modo_seleccionado)
    
    st.divider()
    with st.expander("📂 Cargar Material (PDF/Word)"):
        uploaded_file = st.file_uploader("Sube tu guía aquí", type=['pdf', 'txt', 'docx'])

    if st.button("🔄 Reiniciar Todo", type="primary"):
        st.session_state.clear()
        st.rerun()

# --- 3. LECTURA DE ARCHIVOS ---
contexto_clase = ""
if uploaded_file:
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = pypdf.PdfReader(uploaded_file)
            for page in pdf_reader.pages: contexto_clase += page.extract_text()
        elif "word" in uploaded_file.type:
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs: contexto_clase += para.text + "\n"
        elif uploaded_file.type == "text/plain":
            contexto_clase = uploaded_file.read().decode("utf-8")
        st.sidebar.success(f"✅ Archivo cargado")
    except:
        st.sidebar.error("Error leyendo archivo")

# --- 4. ESTRUCTURA DE 3 PESTAÑAS (TABS) ---
tab_chat, tab_ejercicios, tab_grafica = st.tabs(["💬 Chat con Teo", "🏋️ Zona de Entrenamiento", "📈 Pizarra Gráfica"])

# ==========================================
# PESTAÑA 1: CHAT
# ==========================================
with tab_chat:
    col_img, col_txt = st.columns([1, 2], gap="medium")
    with col_img: st.image("teo_classroom.png")
    with col_txt:
        if modo_seleccionado == "Profesor de Secundaria":
            st.title("Teo - Mentor Académico 🎓")
            st.markdown("Dominemos las matemáticas con estrategia. 🚀")
        else:
            st.title("Hola, soy Teo 🐼")
            st.markdown("¡Vamos a aprender jugando! ✨")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": PROMPT_SISTEMA}]
    
    st.session_state.messages[0] = {"role": "system", "content": PROMPT_SISTEMA}
    
    if contexto_clase and not any("CONTEXTO DEL MATERIAL:" in m["content"] for m in st.session_state.messages):
        st.session_state.messages.append({"role": "system", "content": f"CONTEXTO: {contexto_clase[:3000]}"})

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            icon = "🐼" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=icon): st.markdown(msg["content"])

    if prompt := st.chat_input("Escribe tu pregunta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)
        with st.chat_message("assistant", avatar="🐼"):
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                stream=True
            )
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ==========================================
# PESTAÑA 2: GENERADOR DE EJERCICIOS (REPARADO)
# ==========================================
with tab_ejercicios:
    st.header("🧠 Ponte a prueba")
    col_tema, col_cantidad = st.columns([3, 1])
    with col_tema:
        tema_quiz = st.text_input("Tema a estudiar:", placeholder="Ej: Derivadas, Fracciones...")
    with col_cantidad:
        cantidad_preguntas = st.selectbox("Nº Preguntas:", [5, 10, 15, 20])

    if st.button("📝 Generar Examen"):
        if not tema_quiz and not contexto_clase:
            st.warning("⚠️ Escribe un tema o sube un archivo primero.")
        else:
            with st.spinner(f"Teo está redactando las {cantidad_preguntas} preguntas... ⏳"):
                try:
                    prompt_usuario = f"Genera un quiz de EXACTAMENTE {cantidad_preguntas} preguntas sobre: {tema_quiz}. "
                    if contexto_clase:
                        prompt_usuario += f" Usa este contexto como base: {contexto_clase[:1000]}"

                    respuesta_quiz = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": PROMPT_QUIZ_GENERATOR},
                            {"role": "user", "content": prompt_usuario}
                        ],
                        response_format={"type": "json_object"}
                    )
                    
                    texto_crudo = respuesta_quiz.choices[0].message.content
                    
                    # --- BLOQUE DE SEGURIDAD ANTI-FALLOS ---
                    # 1. Intentamos leer el JSON tal cual
                    try:
                        datos_sucios = json.loads(texto_crudo)
                    except json.JSONDecodeError:
                        # 2. Si falla (Invalid escape), aplicamos cirugía al texto
                        # Reemplazamos \frac por \\frac para que JSON lo acepte
                        texto_reparado = texto_crudo.replace("\\", "\\\\")
                        try:
                            datos_sucios = json.loads(texto_reparado)
                        except:
                            st.error("❌ Error grave de formato en la IA. Intenta de nuevo.")
                            st.stop()
                    
                    # 3. Limpiamos y formateamos para LaTeX visual
                    datos_quiz = sanitizar_json_latex(datos_sucios)
                    # --------------------------------------
                    
                    st.session_state['quiz_actual'] = datos_quiz
                    st.session_state['respuestas_usuario'] = {} 
                    st.session_state['quiz_corregido'] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generando quiz: {e}")

    if 'quiz_actual' in st.session_state:
        quiz = st.session_state['quiz_actual']
        st.subheader(f"📝 {quiz.get('titulo', 'Examen')}")
        with st.form("form_quiz"):
            for i, p in enumerate(quiz['preguntas']):
                st.markdown(f"**{i+1}. {p['pregunta']}**")
                st.radio("Opciones:", p['opciones'], key=f"pregunta_{i}", index=None)
            
            st.divider()
            enviado = st.form_submit_button("✅ Corregir Examen")
            if enviado:
                st.session_state['quiz_corregido'] = True
                st.rerun()

    if st.session_state.get('quiz_corregido', False):
        st.divider()
        st.subheader("📊 Resultados")
        quiz = st.session_state['quiz_actual']
        correctas = 0
        for i, p in enumerate(quiz['preguntas']):
            respuesta_user = st.session_state.get(f"pregunta_{i}")
            if respuesta_user == p['respuesta_correcta']:
                st.success(f"✅ {i+1}. Correcta")
                correctas += 1
            else:
                st.error(f"❌ {i+1}. Incorrecta")
                st.markdown(f"Tu respuesta: **{respuesta_user}** | Correcta: **{p['respuesta_correcta']}**")
            with st.expander(f"💡 Ver explicación"):
                st.write(p['explicacion'])
        
        if len(quiz['preguntas']) > 0:
            puntaje = int((correctas / len(quiz['preguntas'])) * 100)
            st.progress(puntaje)
            st.metric("Calificación", f"{puntaje}% ({correctas}/{len(quiz['preguntas'])})")

# ==========================================
# PESTAÑA 3: PIZARRA GRÁFICA
# ==========================================
with tab_grafica:
    st.header("📈 Visualizador de Funciones")
    st.markdown("Escribe una función y define el rango exacto del eje X para graficar.")

    col_input, col_rango = st.columns([3, 1])
    
    with col_input:
        funcion_input = st.text_input("f(x) =", value="x**2 - 4*x + 3", help="Ejemplos: np.sin(x), x**2, x**3 - 2*x")
    
    with col_rango:
        rango_x = st.number_input("Rango X (+/-)", value=10.0, min_value=0.1, step=1.0)

    if st.button("🎨 Graficar Función"):
        try:
            x = np.linspace(-rango_x, rango_x, 400)
            contexto_seguro = {"x": x, "np": np}
            y = eval(funcion_input, {"__builtins__": None}, contexto_seguro)

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(x, y, label=f"f(x) = {funcion_input}", color="#FF4B4B", linewidth=2)
            
            ax.axhline(0, color='black', linewidth=0.8)
            ax.axvline(0, color='black', linewidth=0.8)
            ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
            ax.legend()
            ax.set_title(f"Gráfico en rango [-{rango_x}, {rango_x}]")
            
            st.pyplot(fig)
            st.info(f"💡 Tip: Estás viendo la función desde x = -{rango_x} hasta x = {rango_x}")
            
        except Exception as e:
            st.error(f"❌ Error al graficar: {e}")
            st.caption("Verifica que la función esté bien escrita (ej: usa `*` para multiplicar).")