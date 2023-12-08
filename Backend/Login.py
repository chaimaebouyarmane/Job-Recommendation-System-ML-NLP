from flask import Flask, request, render_template, redirect, url_for
from Models.User import User
import bcrypt
from BD.Connexion import db

app = Flask(__name__, template_folder='../templates')

collection = db['user']


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error_message = None
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = collection.find_one({'email': email})

        if existing_user:
            error_message = "Cet email existe deja"
        else:

            # Créez un nouvel utilisateur en fournissant tous les arguments nécessaires
            new_user = User(nom, prenom, email, password)

            # Hachez le mot de passe avant de le stocker
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Enregistrez l'utilisateur dans la base de données
            collection.insert_one({'nom': new_user.nom, 'prenom': new_user.prenom, 'email': new_user.email, 'password': hashed_password})

            return redirect(url_for('index_cv'))
    return render_template('index_inscrire.html', error_message=error_message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST' or request.method == 'GET':
        email = request.form.get('email')
        password = request.form.get('password')

        user = collection.find_one({'email': email})

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return redirect('index_cv')
        else :
             error_message = "Email ou mot de passe incorrect"

    return render_template('index.html',error_message=error_message)
# Ajoutez une route pour la page "index_cv.html"
@app.route('/index_cv')
def index_cv():
    return render_template('index_cv.html')


if __name__ == '__main__':
    app.run(debug=True, port=5001)
