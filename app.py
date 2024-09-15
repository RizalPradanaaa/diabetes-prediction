from flask import Flask, request, render_template, flash, send_file, redirect, url_for, flash, session, jsonify
import mysql.connector
import pickle
from openpyxl import Workbook
from io import BytesIO
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecret'

scaler = pickle.load(open('scaler.pkl', 'rb'))
model = pickle.load(open('rf_model.pkl', 'rb'))

# Koneksi database
db_connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="database_diabetes"
)
db_cursor = db_connection.cursor(dictionary=True)

@app.route('/', methods=['GET', 'POST'])
def home():
    prediction = -1
    nama = None
    if request.method == 'POST':
        nama = request.form.get('nama')
        tanggal_lahir = request.form.get('tanggal_lahir')
        kota = request.form.get('kota')
        tempat_tinggal = request.form.get('tempat_tinggal')
        pendidikan = request.form.get('pendidikan')
        bekerja = int(request.form.get('bekerja'))
        sayur = int(request.form.get('sayur'))
        buah = int(request.form.get('buah'))
        makan_manis = int(request.form.get('makan_manis'))
        olahraga = int(request.form.get('olahraga'))

        age = int(request.form.get('age'))
        gender = int(request.form.get('gender'))
        bmi = float(request.form.get('bmi'))
        sbp = float(request.form.get('sbp'))
        dbp = float(request.form.get('dbp'))
        fpg = float(request.form.get('fpg'))
        chol = float(request.form.get('chol'))
        tri = float(request.form.get('tri'))
        hdl = float(request.form.get('hdl'))
        ldl = float(request.form.get('ldl'))
        alt = float(request.form.get('alt'))
        bun = float(request.form.get('bun'))
        ccr = float(request.form.get('ccr'))
        ffpg = float(request.form.get('ffpg'))
        smoking = int(request.form.get('smoking'))
        drinking = int(request.form.get('drinking'))
        family_history = int(request.form.get('family_history'))

        input_features = [[age, gender, bmi, sbp, dbp, fpg, chol, tri, hdl, ldl, alt, bun, ccr, ffpg, smoking, drinking, family_history]]
        # print(input_features)
        prediction = model.predict(scaler.transform(input_features))
        # print(prediction)
        prediction_value = int(prediction[0])

        # Insert data ke MySQL database
        # Insert data ke tabel users
        insert_users_query = """
            INSERT INTO users (nama, tanggal_lahir, kota, tempat_tinggal, pendidikan, bekerja, sayur, buah, makan_manis, olahraga)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        users_data = (nama, tanggal_lahir, kota, tempat_tinggal, pendidikan, bekerja, sayur, buah, makan_manis, olahraga)

        db_cursor.execute(insert_users_query, users_data)
        db_connection.commit()

        # Dapatkan id_user yang baru dimasukkan
        id_user = db_cursor.lastrowid

        # Insert data ke tabel predictions
        insert_predictions_query = """
            INSERT INTO predictions (id_user, age, gender, bmi, sbp, dbp, fpg, chol, tri, hdl, ldl, alt, bun, ccr, ffpg, smoking, drinking, family_history, diabetes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        predictions_data = (id_user, age, gender, bmi, sbp, dbp, fpg, chol, tri, hdl, ldl, alt, bun, ccr, ffpg, smoking, drinking, family_history,  prediction_value)

        db_cursor.execute(insert_predictions_query, predictions_data)
        db_connection.commit()


    return render_template('index.html', prediction=prediction, nama=nama)



# admin
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    # Cek apakah email atau password kosong
    if not email or not password or not confirm_password:
        return jsonify({'message': 'Semua kolom harus diisi.', 'status': 'warning'}), 400

    # Cek apakah password dan konfirmasi password sama
    if password != confirm_password:
        return jsonify({'message': 'Password dan konfirmasi password tidak cocok.', 'status': 'warning'}), 400

    # Cek apakah email sudah terdaftar
    db_cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
    user = db_cursor.fetchone()

    if user:
        return jsonify({'message': 'Email sudah terdaftar.', 'status': 'warning'}), 400

    # Hash password dan simpan ke database
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    db_cursor.execute("INSERT INTO admins (email, password) VALUES (%s, %s)", (email, hashed_password))
    db_connection.commit()

    return jsonify({'message': 'Registrasi berhasil! Silakan login.', 'status': 'success'}), 201

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Pengecekan apakah sudah login
    if 'user_id' in session:
        flash('Anda sudah login.', 'info')
        return redirect(url_for('admin'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Cek apakah email atau password kosong
        if not email or not password:
            flash('Email dan password harus diisi.', 'warning')
            return redirect(url_for('login'))

        # Cek apakah user ada di database
        db_cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
        user = db_cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Login berhasil!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Login gagal. Periksa email dan password Anda.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Hapus sesi user_id
    session.pop('user_id', None)
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    # Pengecekan apakah sudah login
    if 'user_id' not in session:
        flash('Anda harus login terlebih dahulu.', 'danger')
        return redirect(url_for('login'))

    # Ambil nama pengguna yang sedang login
    db_cursor.execute("SELECT email FROM admins WHERE id = %s", (session['user_id'],))
    user = db_cursor.fetchone()
    if user:
        nama_pengguna = user['email']  # Sesuaikan dengan kolom yang sesuai

        # Mengambil data dari tabel predictions dan users
        select_query = """
            SELECT u.nama, u.tanggal_lahir, u.kota, u.tempat_tinggal, u.pendidikan, u.bekerja, u.sayur, u.buah, u.makan_manis, u.olahraga,
                p.age, p.gender, p.bmi, p.sbp, p.dbp, p.fpg, p.chol, p.tri, p.hdl, p.ldl, p.alt, p.bun, p.ccr, p.ffpg, p.smoking, p.drinking, p.family_history, p.diabetes
            FROM predictions p
            JOIN users u ON p.id_user = u.id
        """
        db_cursor.execute(select_query)
        predictions = db_cursor.fetchall()

        total_predictions = len(predictions)
        total_negatif = sum(1 for prediction in predictions if prediction['diabetes'] == 0)
        total_positif = sum(1 for prediction in predictions if prediction['diabetes'] == 1)

        return render_template('admin.html', nama_pengguna=nama_pengguna, predictions=predictions,total_predictions=total_predictions,
                               total_negatif=total_negatif, total_positif=total_positif)
    else:
        flash('Data pengguna tidak ditemukan.', 'danger')
        return redirect(url_for('login'))

@app.route('/report', methods=['GET'])
def report():
    # Ambil semua data dari database
    select_query = """
            SELECT u.id, u.nama, u.tanggal_lahir, u.kota, u.tempat_tinggal, u.pendidikan, u.bekerja, u.sayur, u.buah, u.makan_manis, u.olahraga,
                p.age, p.gender, p.bmi, p.sbp, p.dbp, p.fpg, p.chol, p.tri, p.hdl, p.ldl, p.alt, p.bun, p.ccr, p.ffpg, p.smoking, p.drinking, p.family_history, p.diabetes
            FROM predictions p
            JOIN users u ON p.id_user = u.id
        """
    db_cursor.execute(select_query)
    data = db_cursor.fetchall()

    # Buat file Excel
    wb = Workbook()
    ws = wb.active
    ws.append(['ID', 'Nama Lengkap', 'Tanggal Lahir', 'Kota', 'Tempat Tinggal', 'Pendidikan',
               'Bekerja', 'Sayur', 'Buah', 'Makan Manis', 'Olahraga', 'Usia', 'Gender',
               'BMI', 'SBP', 'DBP', 'FPG', 'Cholesterol', 'Triglycerides', 'HDL',
               'LDL', 'ALT', 'BUN', 'CCR', 'FFPG', 'Smoking', 'Drinking',
               'Riwayat Keluarga', 'Prediksi Diabetes'])

    for row in data:
        # Sesuaikan dengan nama kolom yang benar dari tabel predictions
        ws.append([row['id'], row['nama'], row['tanggal_lahir'], row['kota'], row['tempat_tinggal'],
                   row['pendidikan'], row['bekerja'], row['sayur'], row['buah'], row['makan_manis'],
                   row['olahraga'], row['age'], row['gender'], row['bmi'], row['sbp'], row['dbp'],
                   row['fpg'], row['chol'], row['tri'], row['hdl'], row['ldl'],
                   row['alt'], row['bun'], row['ccr'], row['ffpg'], row['smoking'], row['drinking'],
                   row['family_history'], row['diabetes']])

    # Buat objek BytesIO untuk menulis file Excel
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='data_prediksi.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    app.run(debug=True)
