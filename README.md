# aziotedge-idtranslation-sample

## Instructions
Once edge device gets configured, run the downstream client in _downstream/client.py_ folder from the same machine/VM.
Best to create a python virtualenv and run 

``` bash
python -m pip install -r requirements.txt
```
 before launch it.

```bash
python ./client.py "<DEVICE_ID>" "<DEVICE_SYMM_KEY>"
```