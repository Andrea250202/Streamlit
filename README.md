# TalentPay · Asistente de bandas salariales

Aplicación académica en Python y Streamlit: referencias salariales internas, tabla provincial de convenio y contraste opcional de una oferta. Los Excel ficticios se cargan desde la interfaz y no es necesario subirlos a GitHub.

## Subir a GitHub y desplegar

1. Crea un repositorio en GitHub.
2. Sube `app.py`, `requirements.txt` y este `README.md` a la raíz del repositorio.
3. En Streamlit Community Cloud, crea una aplicación y selecciona el repositorio, la rama `main` y el archivo `app.py`.
4. Pulsa Deploy. Una vez abierta, carga los dos Excel desde el panel lateral.

Si deseas restringir el prototipo con contraseña, añade en la configuración Secrets de Streamlit:

```toml
APP_PASSWORD = "sustituye-por-una-contraseña-larga"
```

No publiques la contraseña en GitHub. Sin ella, la aplicación funciona en modo demostración. El control mediante contraseña compartida es básico; para datos reales se necesita autenticación corporativa y un entorno aprobado por la empresa. Esta aplicación no constituye una garantía de seguridad para información real.

## Ejecutar en tu ordenador

Con Python 3.11 o 3.12 instalado, abre una terminal en la carpeta y ejecuta:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Archivos de entrada

Primera fila con los encabezados exactos. Puedes seleccionar la hoja desde la interfaz.

**Headcount:** `ID_Empleado`, `Puesto`, `Provincia`, `Nivel de experiencia`, `Salario bruto anual`.

**Convenios:** `Provincia`, `Categoría profesional`, `Salario convenio bruto anual`.

Los salarios deben ser números en euros brutos anuales a jornada completa. Los del convenio incluyen todos los conceptos y los mantiene Administración. No se consultan fuentes externas ni se comprueba la vigencia legal. Los perfiles son Junior (menos de 3 años), Intermedio (desde 3 hasta menos de 6) y Sénior (6 o más), como criterio interno ficticio.

Se necesitan cinco empleados comparables; si no existen, puede ampliarse voluntariamente la búsqueda a todas las provincias. Los empleados con ID duplicado se excluyen en todas sus apariciones. Los convenios con importes contradictorios se rechazan para corregirlos. El gráfico solo contiene recuentos por intervalos, no salarios individuales.

La aplicación utiliza la última versión cargada. El botón Actualizar vuelve a procesarla; para incorporar cambios guardados en el archivo original hay que volver a cargarlo. No existe sincronización automática con los Excel de tu ordenador.

## Confidencialidad y alcance

Utiliza los datos ficticios para la entrega y el despliegue académico. No subas Excel reales ni claves al repositorio. No se usa ninguna API de IA ni se envían los archivos a un modelo externo; cuando despliegas la aplicación, los Excel cargados se procesan en el servidor de Streamlit. Los resultados son orientativos y la clasificación profesional requiere revisión de RR. HH.
