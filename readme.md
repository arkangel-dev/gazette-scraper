# gazette-scraper

Library to scrape data from [gazette.gov.mv](https://gazette.gov.mv) with integrated Bing Translate.



## Usage

```python
from gazettescrape import GazetteScraper
from gazettescrape import ListingType
from gazettescrape import JobType

sesh = GazetteScraper()
sesh.ScrapeListings(ListingType.JobOpportunities, JobType.InformationTechnology)
```

```
Processing page 1
[
    {
        "id": "171530",
        "source": "Maldives National University",
        "description": "Computer Technology (Faculty of Education)",
        "voided": false,
        "deadline": "05 December 2021, 12:00",
        "date": "29 November 2021",
        "link": "https://www.gazette.gov.mv/iulaan/171530"
    }
]
```





