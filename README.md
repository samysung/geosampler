# Geosampler

## Why this project?


## Installation

### Install requirements

As Gdal dependencies are presents it's preferable to
install dependencis via conda before installing the package:
```bash
  git clone https://github.com/samysung/geosampler
  cd geosampler/packaging
  conda env create -f package_env.yml
  ```
### From pip:

  ```bash
  pip install geosampler
  # or
  pip install geosampler==X.Y # for a specific version
  ```

<details>
  <summary>Other installation options</summary>

  #### From source:

  ```bash
  python setup.py install
  ```

  #### From source with symbolic links:

  ```bash
  pip install -e .
  ```

  #### From source using pip:

  ```bash
  pip install git+https://github.com/samysung/geosampler
  ```

</details>
