
### Example run:

```
python runmodel.py -s example_data/alignment.fasta -iqtree iqtree3 -l 1321 \
   -txt example_data/models.txt -m example_data/C10F.nex \
   -threads 30
```
The results will be saved in **the same directory** as `alignment.fasta`, including two subfolders: `output_model` and `output_simulation`.

The expected summary results file, `PBT_summary.md`, will be stored inside the `output_simulation` directory.

In addition, all models defined in the C10F.nex file are provided for demonstration purposes only and do not have practical significance.
