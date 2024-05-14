# 🌸 PetalVault

| ![Project logo](icons/icon.svg) | <h1>Secure cold password manager with AES+BIP39 encryption and QR code-based synchronization</h1> |
| ------------------------------- | :-----------------------------------------------------------------------------------------------: |

<div style="width:100%;text-align:center;">
    <p align="center">
        <img src="https://badges.frapsoft.com/os/v1/open-source.png?v=103" >
    </p>
</div>

----------

## 😋 Support project

> 💜 Please support the project

- BTC: `bc1qaj2ef2jlrt2uafn4kc9cmscuu8yqkjkvxxr5zu`
- ETH: `0x284E6121362ea1C69528eDEdc309fC8b90fA5578`
- ZEC: `t1Jb5tH61zcSTy2QyfsxftUEWHikdSYpPoz`

- Or by my music on [🔷 bandcamp](https://f3rni.bandcamp.com/)

- Or [message me](https://t.me/f33rni) if you would like to donate in other way 💰

----------

## ⚠️ Disclaimer

### PetalVault is under development

> Use at your own risk. The author of the repository is **not** responsible for any damage caused by the repository, the application, or its components

----------

## 🚧 README in progress

Wait for the README or test app yourself 🙃

----------

## 🏗️ Execute or build from source

- Install Python (tested on **3.11** only)
- Clone repo

    ```shell
    git clone https://github.com/F33RNI/PetalVault
    cd PetalVault
    ```

- Create virtual environment and install dependencies

    ```shell
    python -m venv venv

    # For Linux
    source venv/bin/activate

    # For Windows
    venv\Scripts\activate.bat

    pip install -r requirements.txt --upgrade
    ```

- **Launch** PetalVault

    ```shell
    python main.py --verbose
    ```

- **Build** using PyInstaller

    ```shell
    pip install pyinstaller
    pyinstaller main.spec

    # Executable will be inside dist/ directory
    ```

----------

## ✨ Contribution

- Anyone can contribute! Just create a **pull request**
