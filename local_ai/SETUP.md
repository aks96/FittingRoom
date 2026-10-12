# yourFittingRoom desktop companion — private beta

Photos remain on your own computer. This companion listens only at 127.0.0.1:8765.

Tested: Apple M5 MacBook, 16 GB memory. Other GPUs and clean installations still need validation. Use a current desktop Chrome browser. Some browsers require a local-network permission; approve it only for the yourFittingRoom site. Phones are not supported for generation.

1. Install Python 3.12 from python.org if needed. Extract this archive into a folder you own.
2. Open Terminal in that folder. Run `./scripts/setup-ai.sh`. It downloads several GB of model files from official upstream repositories. Initial setup needs internet; it does not process personal photos. Read the upstream model licenses before redistribution or commercial use.
3. Run `./scripts/ai.sh`. Keep this terminal open. Model integrity is checked on startup. Copy its private pairing code.
4. Open the private yourFittingRoom link, enter the pairing code and enable the local-processing consent checkbox. Credentials last four hours and stay in this browser tab's memory. Refreshing requires pairing again.
5. Select the clothing and your photo. Sign in when ready to generate. Site access is also restricted to invited testers during the beta.
6. To clear engine memory, stop it with Ctrl-C. To revoke all pairing credentials, restart it. Delete downloads yourself; they are separate files on your device.

Never expose port 8765 to your network, reverse proxy it, or bind it to 0.0.0.0. Never share the pairing code. Only pair on the exact yourFittingRoom site listed in security/issuer.json. Do not turn off browser security to establish a connection. Contact the beta owner if your browser blocks local connections.

Security changes to the hosted signing key require distributing an updated companion public key. Generation permissions expire after two minutes; model processing may take longer. Processing is a style approximation and does not predict physical fit, size or material behavior.
