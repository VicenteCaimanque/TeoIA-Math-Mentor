from openai import OpenAI
import os

# --- AQUÍ VA TU CLAVE DE OPENAI ---
# Borra el texto de relleno y pega tu clave que empieza con "sk-proj..."
CLAVE_OPENAI = "TU_API_KEY_AQUI"
# Configuración del cliente
try:
    client = OpenAI(api_key=CLAVE_OPENAI)
except Exception as e:
    print(f"Error de configuración: {e}")
    exit()

# --- PROMPT MAESTRO (TEO) ---
PROMPT_SISTEMA = """
Eres 'Teo', un tutor de matemáticas para niños de primaria.
Personalidad: Paciente, amigable y divertido.
REGLA: Nunca des la respuesta directa. Guía al estudiante con preguntas.
"""

# Historial para recordar la conversación
historial = [
    {"role": "system", "content": PROMPT_SISTEMA}
]

def iniciar():
    print("\n" + "="*40)
    print("🤖 ¡HOLA! SOY TEO (Versión OpenAI Pagada)")
    print("   Escribe 'salir' para cerrar.")
    print("="*40 + "\n")

    while True:
        try:
            texto = input("Tú: ")
            if texto.lower() in ['salir', 'chau', 'adios']:
                print("Teo: ¡Nos vemos!")
                break
            
            # Guardamos tu pregunta
            historial.append({"role": "user", "content": texto})

            # Enviamos a OpenAI (Usamos gpt-4o o gpt-4o-mini que es más barato)
            completion = client.chat.completions.create(
                model="gpt-4o", 
                messages=historial
            )

            respuesta = completion.choices[0].message.content
            
            # Guardamos la respuesta de la IA y la mostramos
            historial.append({"role": "assistant", "content": respuesta})
            print(f"Teo: {respuesta}")
            print("-" * 20)

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Revisa si tus 5 dólares ya se acreditaron o si copiaste bien la clave.")
            break

if __name__ == "__main__":
    iniciar()