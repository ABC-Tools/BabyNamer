# AI Baby Namer


## Data source of name frequency
https://www.ssa.gov/data.json; the exact record is
```
"dataQuality": null,
"describedBy": "https://www.ssa.gov/oact/babynames/background.html",
"describedByType": null,
"description": "The data (name, year of birth, sex, and number) are from a 100 percent sample of Social Security card applications for 1880 onward.",
"distribution": [
        {
          "description": null,
          "downloadURL": "https://www.ssa.gov/oact/babynames/names.zip",
          "format": "ZIP",
          "mediaType": "application/zip",
          "title": null
        }
]
```

## Data source for name meaning
https://nameberry.com/popular-names/us/all

https://nameberry.com/popular-names/us/girls/all

https://nameberry.com/popular-names/us/boys/all

1. use Scrapy to scrape the data
2. call ChatGPT to rewrite the content (tools/babyberry_result_rewriting.py)

## Development

### test code using local docker
```
$ docker compose up
$ curl http://127.0.0.1:8080/babyname/name_facts?name=Barbara
```

### test code in python shell
```commandline
$ . venv/bin/activate
$ sudo Python (sudo is required for disk access)
>>> from importlib import reload
>>> import tools.babyberry_result_rewriting as brr
>>> .... 
>>> (change babyberry_result_rewriting file)
>>> reload(brr)
```

### Python type cheat sheet
https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
