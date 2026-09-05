# Diagrama de arquitetura (as-code)

Fonte versionada do diagrama oficial da AWS, gerada com a biblioteca
[`diagrams`](https://diagrams.mingrammer.com) (ícones oficiais AWS).

## Pré-requisitos
- **Graphviz** (binário `dot`): `sudo apt install graphviz` · `brew install graphviz`
- `pip install diagrams`

## Gerar a imagem
```bash
python docs/architecture/diagram.py
# -> docs/architecture/condoguard_architecture.png
```

A imagem gerada é referenciada por [`../ARCHITECTURE.md`](../ARCHITECTURE.md). O `.png`
não é versionado por padrão (é artefato de build); gere-o localmente ou no CI conforme necessário.
