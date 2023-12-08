import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.blocking import BlockingScheduler  # Importez BlockingScheduler
from pymongo import MongoClient
from BD.Connexion import db, client
from Models.OffreEmploi import OffreEmploi
from sklearn.model_selection import train_test_split
from Models.offres_emploi_train import OffreEmploiTrain
from Models.offres_emploi_test import OffreEmploiTest
import time 

def scrape_job_offers():
    # Sélectionnez la collection dans la base de données
    collection = db["offres_emploi"]

    # Récupérez les liens des offres déjà enregistrées
    existing_links = set(doc["lien"] for doc in collection.find({}, {"lien": 1}))

    # Start with the initial URL
    url = "https://www.stagiaires.ma/offres-stages"
    data = []
    while url:
        response = None
        while response is None:
            try:
                response = requests.get(url)
            except requests.exceptions.RequestException as e:
                print(f"Erreur de connexion : {e}")
                time.sleep(5)  # Attendre pendant 5 secondes avant de réessayer

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            target_classes = ["offer-container p-xxs m-b-xs", "offer-container p-xxs m-b-xs bg-muted"]
            for x in soup.find_all(class_=target_classes):
                div = x.find('a')
                lien = div['href']
                if lien not in existing_links:  # Vérifiez si le lien n'existe pas déjà
                    response3 = requests.get(lien)
                    if response3.status_code == 200:
                        soup3 = BeautifulSoup(response3.text, 'html.parser')
                        name = soup3.find('h4', class_="inline").text
                        div_element = soup3.find('div', class_='well well-sm m-b-none')  # Localisez la <div> cible
                        if div_element:
                            paragraphs = div_element.find_all('p')  # Trouvez tous les éléments <p> dans la <div>
                            # Initialisez une chaîne vide pour stocker le texte combiné
                            combined_text = ''
                            for paragraph in paragraphs:
                                combined_text += paragraph.text + ' '

                            # Créez un dictionnaire pour les données extraites
                            entry = {
                                "Entreprise": name,
                                "Description": combined_text,
                                "Lien": lien
                            }

                            data.append(entry)
                    else:
                        print(f"Erreur de connexion lors de la récupération de {lien}")

            # Trouvez l'élément <ul> avec la classe "pagination"
            pagination_ul = soup.find('ul', class_='pagination')

            # Vérifiez s'il y a un lien "suivant"
            next_link = pagination_ul.find('li', class_='next')
            if next_link:
                link = next_link.find('a')
                if link:
                    url = link['href']
                    print(f"Next Link Href: {url}")
            else:
                url = None

    # Insérez toutes les données scrappées dans la collection "OffreEmploi"
    for entry in data:
        offre_emploi = OffreEmploi(name=entry["Entreprise"], combined_text=entry["Description"], lien=entry["Lien"])
        collection.insert_one(offre_emploi.__dict__)

    # Divisez les données en ensembles d'entraînement et de test (par exemple, 80% d'entraînement, 20% de test)
    train_data, test_data = train_test_split(data, test_size=0.2, random_state=42)

    # Créez des collections distinctes pour les données d'entraînement et de test
    train_collection = db["offres_emploi_train"]
    test_collection = db["offres_emploi_test"]

    # Parcourez les données d'entraînement et insérez-les dans la collection d'entraînement
    for entry in train_data:
        offre_emploi_train = OffreEmploiTrain(name=entry["Entreprise"], combined_text=entry["Description"], lien=entry["Lien"])
        train_collection.insert_one(offre_emploi_train.__dict__)

    # Parcourez les données de test et insérez-les dans la collection de test
    for entry in test_data:
        offre_emploi_test = OffreEmploiTest(name=entry["Entreprise"], combined_text=entry["Description"], lien=entry["Lien"])
        test_collection.insert_one(offre_emploi_test.__dict__)

    # Fermez la connexion MongoDB
    client.close()

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(scrape_job_offers, 'cron', hour=6)  # Planifiez l'exécution de scrape_job_offers tous les jours à 6h du matin
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass