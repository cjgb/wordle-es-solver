# Solve the Spanish daily Wordle game

The repo contains code in both R and Python to solve the daily Wordle game in Spanish.

## Usage

Both scripts have the same interface:

```
python wordle.py furor
python wordle.py furor aireo

Rscript wordle.R furor
Rscript wordle.R furor aireo
```

## Notes

- The second argument (optional) is the first candidate. The default is `seria`.
- Both scripts implement the very same algorithm on the very same data.
- Code will not break gracefully in case of errors (say, if your candidate has more than five characters).

