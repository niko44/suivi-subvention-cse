# suivi-subvention-cse

Cette application permet de suivre ses demandes de subvention de son CSE.

# Architecture
L'application s'appuie sur Flask lui permettant d'être très léger et simple à déployer. Le modèle de données est défini dans le fichier models.py et la BDD est créée automatiquement au démarrage si elle n'existe pas déjà.

L'image Docker est automatiquement construite et déposée sur le repo Docker Hub : [niko44/suivi-subvention-cse](https://hub.docker.com/repository/docker/niko44/suivi-subvention-cse)

Pour des raisons de simplicité l'application n'est pas conçue pour être déployée à l'échelle. En effet la base de données SQLite est intégrée au conteneur. Toutefois il est possible, et recommandé, d'utiliser un montage pour stocker le fichier de la BDD en dehors du conteneur (cf. Déploiement). De même, il est recommandé d'utiliser un autre montage pour le stockage des fichiers uploadés (comme les factures par exemple).

# Sécurité
* L'application au démarrage crée un utilisateur *admin* dont le mot de passe est *admin123*. Il est fortement recommandé de le modifier à la première connexion.
* Cet utilisateur ne peut être supprimé mais il est possible d'attribuer ce rôle à d'autres utilisateurs ultérieurement. Toutefois, un utilisateur créé en tant qu'administrateur ne sera pas considéré comme un salarié. Il faut en premier créer le salarié et ensuite seulement lui attribué le rôle administrateur.
* Une fois connecté, l'application génère un cookie de session signé à l'aide de la clé 'SECRET_KEY'. Cette clé est à passer via une variable d'environnement au démarrage du conteneur.
* Tous les identifiants techniques sont générés aléatoirement

# Déploiement
Par défaut les données sont stockées à l'intérieur du conteneur, donc si celui-ci est supprimé les données le seront aussi. Pour sauvegarder ces données il faut indiquer 2 montages distincts :
| Montage local | Montage conteneur | Commentaire |
| ------------- |:-------------:|-------------|
| /repertoire_local_upload     | /app/upload     | Répertoire où seront sauvegardés les fichiers uploadés (PDF, JPG, PNG, etc)|
| /repertoire_local _bdd     | /app/bdd    | Répertoire où est stocké le fichier de la BDD|

Déployer l'image Docker avec ces paramètres :
```
docker run -d -p 5100:5100 --name suivi-subvention-cse  -v /volume3/docker/cse/upload:/app/upload -v /volume3/docker/cse/bdd:/app/bdd -e SECRET_KEY=[VOTRE CLE]  suivi-subvention-cse
```
