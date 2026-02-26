# Smarter Shutter

[English](#english) | [Francais](#francais)

---

## English

Position tracking for shutters and blinds that don't report their position natively.

Many motorized shutters only support open, close and stop. They have no idea where they actually are between fully open and fully closed. Smarter Shutter solves this by measuring travel time and calculating the position in real time.

You get a proper cover entity with a percentage slider, intermediate positioning and state restoration after restart.

### What it does

- Opens, closes and **stops at any position** (0-100%)
- Tracks position in real time based on travel duration
- Restores the last known position after a Home Assistant restart
- Detects movements triggered by wall switches or physical buttons
- Recalibrates automatically when the shutter reaches a known end stop

### Requirements

- Home Assistant 2024.1.0 or newer
- A shutter controlled by one of:
  - **Two relay switches** (one for up, one for down) -- typical with Zigbee modules like ZBMINIR2
  - **An existing cover entity** that lacks position tracking

### Installation

1. Install via [HACS](https://hacs.xyz): search for "Smarter Shutter"
2. Restart Home Assistant
3. Go to **Settings > Devices & Services > Add Integration** and search for "Smarter Shutter"

### Setup

The setup wizard walks you through four steps.

**1. Name and control mode**

Give your shutter a name and choose how it is controlled: two relay switches or an existing cover entity.

**2. Entity selection**

- *Relay mode*: pick the switch that opens (moves up) and the one that closes (moves down)
- *Cover mode*: pick the existing cover entity to enhance

**3. Travel times**

Grab a stopwatch and measure:
- How long from fully closed to fully open
- How long from fully open to fully closed
- The motor reaction delay (time between sending a command and the motor actually moving). Set to 0 if it reacts instantly.

**4. Stop method**

Choose how the integration should stop the motor:
- **Send a stop command** -- works with most devices
- **Send direction again to toggle off** -- for devices that don't support a stop command (common with some Zigbee relays). This resends the current direction to cut the motor.

### Adjusting after installation

Go to **Settings > Devices & Services > Smarter Shutter** and click **Configure**. You can fine-tune the travel times, the reaction delay and the stop method without deleting the integration.

### How it works

The integration calculates the shutter position using a simple formula: if the shutter takes 30 seconds to fully open and has been moving up for 15 seconds, it is at 50%.

When you request a specific position, the integration starts the motor, waits the calculated amount of time, then stops it. The position updates every second in the UI.

At full open (100%) or full close (0%), the integration recalibrates to compensate for any drift that may have accumulated over multiple partial movements.

### Supported features

| Feature | Supported |
|---------|-----------|
| Open / Close / Stop | Yes |
| Set position (0-100%) | Yes |
| Position tracking | Yes |
| State restoration | Yes |
| Wall switch detection | Yes |
| End stop recalibration | Yes |
| Two relay switches | Yes |
| Existing cover entity | Yes |

### Troubleshooting

**The shutter doesn't stop at the requested position**

Your device probably doesn't support the stop command. Go to the integration options and change the stop method to "Send direction again to toggle off".

**The position drifts over time**

The travel times in the configuration may not be accurate. Measure them again with a stopwatch and update the values in the integration options. The drift resets every time the shutter reaches a full open or full close position.

**The shutter doesn't react to wall switch presses**

Make sure the relay entities are the same ones configured in the integration. Check the Home Assistant logs for any errors from `smarter_shutter`.

---

## Francais

Suivi de position pour les volets et stores qui ne remontent pas leur position nativement.

Beaucoup de volets motorises ne supportent que ouvrir, fermer et stop. Ils ne savent pas ou ils se trouvent entre completement ouvert et completement ferme. Smarter Shutter resout ce probleme en mesurant le temps de course et en calculant la position en temps reel.

Vous obtenez une entite cover avec un curseur en pourcentage, le positionnement intermediaire et la restauration de l'etat apres redemarrage.

### Ce que ca fait

- Ouvre, ferme et **s'arrete a n'importe quelle position** (0-100%)
- Suit la position en temps reel a partir de la duree de course
- Restaure la derniere position connue apres un redemarrage de Home Assistant
- Detecte les mouvements declenchés par les interrupteurs muraux ou boutons physiques
- Se recalibre automatiquement quand le volet atteint une butee

### Pre-requis

- Home Assistant 2024.1.0 ou plus recent
- Un volet pilote par :
  - **Deux relais** (un pour monter, un pour descendre) -- typique avec les modules Zigbee comme le ZBMINIR2
  - **Une entite cover existante** qui ne gere pas le positionnement

### Installation

1. Installer via [HACS](https://hacs.xyz) : chercher "Smarter Shutter"
2. Redemarrer Home Assistant
3. Aller dans **Parametres > Appareils et services > Ajouter une integration** et chercher "Smarter Shutter"

### Configuration

L'assistant de configuration se deroule en quatre etapes.

**1. Nom et mode de pilotage**

Donnez un nom a votre volet et choisissez comment il est pilote : deux relais ou une entite cover existante.

**2. Selection des entites**

- *Mode relais* : choisissez le relais qui ouvre (montee) et celui qui ferme (descente)
- *Mode cover* : choisissez le volet existant a enrichir

**3. Temps de course**

Chronometre en main, mesurez :
- Le temps de completement ferme a completement ouvert
- Le temps de completement ouvert a completement ferme
- Le delai de reaction du moteur (temps entre l'envoi d'une commande et le debut reel du mouvement). Mettez 0 si le moteur reagit instantanement.

**4. Methode d'arret**

Choisissez comment l'integration doit arreter le moteur :
- **Envoyer une commande d'arret** -- fonctionne avec la plupart des appareils
- **Renvoyer le sens pour couper le moteur** -- pour les appareils qui ne supportent pas la commande stop (frequent avec certains relais Zigbee). L'integration renvoie la commande de direction en cours pour basculer le moteur.

### Ajustement apres installation

Allez dans **Parametres > Appareils et services > Smarter Shutter** et cliquez sur **Configurer**. Vous pouvez affiner les temps de course, le delai de reaction et la methode d'arret sans supprimer l'integration.

### Comment ca fonctionne

L'integration calcule la position du volet avec une formule simple : si le volet met 30 secondes a s'ouvrir completement et qu'il monte depuis 15 secondes, il est a 50%.

Quand vous demandez une position precise, l'integration demarre le moteur, attend le temps calcule, puis l'arrete. La position se met a jour chaque seconde dans l'interface.

A l'ouverture complete (100%) ou la fermeture complete (0%), l'integration se recalibre pour compenser la derive qui a pu s'accumuler sur plusieurs mouvements partiels.

### Fonctionnalites supportees

| Fonctionnalite | Supportee |
|----------------|-----------|
| Ouvrir / Fermer / Stop | Oui |
| Positionnement (0-100%) | Oui |
| Suivi de position | Oui |
| Restauration d'etat | Oui |
| Detection interrupteur mural | Oui |
| Recalibration en butee | Oui |
| Deux relais | Oui |
| Entite cover existante | Oui |

### Depannage

**Le volet ne s'arrete pas a la position demandee**

Votre appareil ne supporte probablement pas la commande stop. Allez dans les options de l'integration et changez la methode d'arret pour "Renvoyer le sens pour couper le moteur".

**La position derive avec le temps**

Les temps de course dans la configuration ne sont peut-etre pas assez precis. Mesurez-les a nouveau avec un chronometre et mettez a jour les valeurs dans les options de l'integration. La derive se remet a zero chaque fois que le volet atteint l'ouverture ou la fermeture complete.

**Le volet ne reagit pas aux appuis sur l'interrupteur mural**

Verifiez que les entites relais sont bien celles configurees dans l'integration. Consultez les logs de Home Assistant pour d'eventuelles erreurs de `smarter_shutter`.

---

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
