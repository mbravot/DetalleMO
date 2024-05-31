from flask import Flask, request, Response, render_template
import mysql.connector
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, PageBreak, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
import io

app = Flask(__name__)

def create_table(data, font_size):
    pdf_width, pdf_height = landscape(letter)
    col_widths = [(pdf_width - 8) / len(data[0])] * len(data[0])
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
    ]))
    return table

def fetch_data_from_db(año, mes, sucursal):
    db = mysql.connector.connect(
        host="186.64.119.90",
        user="agrico24_mbravo",
        password="Inicio01*",
        database="agrico24_Tarjas_LH"
    )
    cursor = db.cursor()
    query = ("SELECT fecha, labor, centro_de_costo, trabajador, horas_trab, unidad_de_control, rendimiento, tarifa, "
             "total_trato_jornada, cant_hrs_extra, valor_hr_extra, monto_hrs_extra, ROUND(total_dia, 0) AS total_dia "
             "FROM Detalle_MO WHERE YEAR(fecha) = %s AND mes = %s AND id_sucursal = %s "
             "ORDER BY trabajador, fecha")
    cursor.execute(query, (año, mes, sucursal))
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return data

def generate_pdf(año, mes, sucursal):
    data = fetch_data_from_db(año, mes, sucursal)
    if not data:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=4, leftMargin=4, topMargin=5, bottomMargin=4)
    elements = []

    trabajador_actual = None
    table_data = []

    for row in data:
        fecha, labor, centro_de_costo, trabajador, horas_trab, unidad_de_control, rendimiento, tarifa, total_trato_jornada, cant_hrs_extra, valor_hr_extra, monto_hrs_extra, total_dia = row

        if trabajador != trabajador_actual:
            if trabajador_actual is not None and table_data:
                add_summary_row_and_table(elements, table_data, trabajador_actual)
                table_data = []

            trabajador_actual = trabajador
            if not table_data:
                table_data.append(["Fecha", "Labor", "Centro de Costo", "Horas Trabajadas", "Unidad de Control", "Rendimiento", "Tarifa", "Total Trato/Jornada", "Cantidad Hrs Extra", "Valor Hr Extra", "Monto Hrs Extra", "Total Día"])

        table_data.append([fecha, labor, centro_de_costo, horas_trab, unidad_de_control, rendimiento, tarifa, total_trato_jornada, cant_hrs_extra, valor_hr_extra, monto_hrs_extra, total_dia])

    if table_data:
        add_summary_row_and_table(elements, table_data, trabajador_actual)

    try:
        doc.build(elements)
    except Exception as e:
        print(f"Error al generar el PDF: {e}")
        return None

    buffer.seek(0)
    return buffer

def add_summary_row_and_table(elements, table_data, trabajador_actual):
    def safe_float(value):
        try:
            return float(value) if value is not None else 0
        except ValueError:
            return 0
        
         # Agregando print para depuración
    for row in table_data[1:]:
        print(f"Procesando fila: {row}")
        
    total_trato_sum = int(sum(safe_float(row[7]) for row in table_data[1:]))
    cant_hrs_extra_sum = sum(safe_float(row[8]) for row in table_data[1:])
    total_he_sum = int(sum(safe_float(row[10]) for row in table_data[1:]))
    total_dia_sum = int(sum(safe_float(row[11]) for row in table_data[1:]))

    table_data.append(["", "", "", "", "", "", "", f"T. Tratos: ${total_trato_sum}", f"Cant. HE: {cant_hrs_extra_sum:.2f}", "", f"T. HE: ${total_he_sum}", f"T. Mes: ${total_dia_sum}"])
    font_size = 6
    table = create_table(table_data, font_size)
    elements.append(Paragraph(f"Trabajador: {trabajador_actual}", ParagraphStyle(name="CustomStyle", fontSize=font_size)))
    elements.append(table)
    elements.append(PageBreak())

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf_route():
    año_seleccionado = request.form.get('año')
    mes_seleccionado = request.form.get('mes')
    sucursal_seleccionada = request.form.get('sucursal')
    pdf_buffer = generate_pdf(año_seleccionado, mes_seleccionado, sucursal_seleccionada)

    if pdf_buffer:
        response = Response(pdf_buffer.read(), mimetype='application/pdf')
        response.headers['Content-Disposition'] = f'attachment; filename="Detalle_Mano_de_Obra_{año_seleccionado}_{mes_seleccionado}_Sucursal_{sucursal_seleccionada}.pdf"'
        return response
    else:
        return "No hay datos disponibles para el año, mes y sucursal seleccionados."

if __name__ == '__main__':
    app.run(debug=True)
