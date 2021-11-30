import requests
import re
import json
import btranslate
import time 

from enum import Enum
from lxml import html
from requests.models import Response
from typing import List


class ListingType(Enum):
    All                 = ''
    Work                = 'masakkaiy'
    WantedForPurchase   = 'gannan-beynunvaa'
    RentingOut          = 'kuyyah-dhinun'
    RentingIn           = 'kuyyah-hifun'
    JobOpportunities    = 'vazeefaa'
    Education           = 'thamreenu'
    Auction             = 'neelan'
    Information         = 'aanmu-mauloomaathu'
    Telling             = 'dhennevun'
    Competition         = 'mubaaraaiy'
    NewsSnippets        = 'noos-bayaan'
    Insurance           = 'insurance'
    Tender              = 'beelan'

    def __init__(self, _shortcode):
        self.shortcode = _shortcode

class JobType(Enum):
    All                         = ''
    Administration              = 'administration'
    PublicRelations             = 'public-relations'
    Construction                = 'construction'
    Education                   = 'education'
    FinanceAndAccount           = 'finance'
    HealthCare                  = 'health-care'
    HumanResources              = 'human-resources'
    InformationTechnology       = 'information-technology'
    Insurance                   = 'insurance'
    PublishingAndJournalism     = 'publishing-and-journalism'
    Transport                   = 'transport'
    Legal                       = 'legal'
    Technical                   = 'technical'
    CustomerService             = 'customer-service'
    Maintenance                 = 'maintenance'
    SupportStaff                = 'support-staff'
    Mechanical                  = 'mechanical'
    Management                  = 'management'

    def __init__(self, _shortcode):
        self.shortcode = _shortcode

class GazetteScraper:

    BaseUrl = 'https://www.gazette.gov.mv/iulaan'
    UserAgent = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    Session = None
    TranslateAgent = None

    translateCooldownTime = 1.5
    lastTranslateTimeStamp = -1

    def __init__(self):
        self.Session = requests.session()
        self.Session.headers.update(self.UserAgent)
        self.TranslateAgent = btranslate.Translator()
        self.TranslateAgent.fetchGlobalConfig()

    def ScrapeListings(self, type:ListingType=ListingType.All, jobtype:JobType=JobType.All, Office='', Description='', StartDate='', EndDate='', FilterInactiveListings = True, PageRange:str='1'):
        # Scrape data from Gazette.gov.mv.
        # type : ListingType: Select which type of listing to get. Defaults to all listings
        # jobType : JobType : Select which type of jobs to filter. Defaults to all types of jobs
        # Office : The source of the listing
        # Description : The description of the listing
        # StartDate : The start date of the listing (DD-MM-YYYY)
        # EndDate : End deadline for the listing (DD-MM-YYYY)
        # FilterInactiveListings : Dont show listings past its deadline
        # PageRange : Select which pages to scrape. Use commas and - to separate pages and ranges. Or type all to scrape all the listings
        
        searchParams = '?'
        searchParams += 'type=' + type.shortcode

        if type == ListingType.JobOpportunities: searchParams += '&job-category=' + jobtype.shortcode
        if re.match('[0-9]{2}-[0-9]{2}-[0-9]{4}', StartDate): searchParams += '&start-date=' + StartDate
        if re.match('[0-9]{2}-[0-9]{2}-[0-9]{4}', EndDate): searchParams += '&end-date=' + EndDate
        if not Office == '': searchParams += '&office=' + Office
        if not Description == '': searchParams += '&q=' + Description
        if FilterInactiveListings: searchParams += '&open-only=1'

        results = []

        if PageRange.lower() == 'all':
            i = 0
            while True:
                r = self.GetListingResults(self.BaseUrl + searchParams + '&page=' + str(i))
                if len(r) == 0: break
                i += 1
                results.extend(r)
        else:
            rangeSelections = PageRange.split(',')
            for r in rangeSelections:
                if len(r.split('-')) > 1:
                    start = int(r.split('-')[0])
                    end = int(r.split('-')[1])

                    for i in range(start, end + 1):
                        print("Processing page " + str(i))
                        r = self.GetListingResults(self.BaseUrl + searchParams + '&page=' + str(i))
                        results.extend(r)
                else:
                    print("Processing page " + str(r))
                    r = self.GetListingResults(self.BaseUrl + searchParams + '&page=' + str(r))
                    results.extend(r)
                
        print(json.dumps(results, indent=4))

    def GetListingResults(self, url:str) -> dict:
        # Gets the listings from a single page of the gazette page. It will return some basic information of the listing
        # along with a link to a page with more details of the listing
        response = self.Session.get(url)
        if response.status_code != 200:
            print("Warning : Failed to process page (Status code " + response.status_code + ")...")
            return []
        bp = html.fromstring(response.content.decode('utf-8'))
        listings = bp.xpath("//div[@id='gazette-main-wrapper']/div[2]/div[@class='col-md-12 bordered items ']")
        listingDict = []
        for li in listings:
            sourceOffice = self.TranslateFromMV(li.xpath("div[1]/div[2]/a/text()")[0].lstrip().rstrip())
            description = self.TranslateFromMV(li.xpath("div[2]/a/text()")[0].lstrip().rstrip())
            deadLine = self.ConvertDateToEnglish(li.xpath("div[3]/div[2]/text()")[0].rstrip().lstrip()[10:])
            infoLink = li.xpath("div[3]/div[3]/a/@href")[0]
            voided = len(li.xpath("div[2]/p[@class='retracted']")) != 0
            date = self.ConvertDateToEnglish(li.xpath("div[3]/div[1]/text()")[0].lstrip()[7:].lstrip().rstrip())
            listing_id = infoLink.split('/')[-1]

            ldict = {
                'id' : listing_id,
                'source' : sourceOffice,
                'description' : description,
                'voided' : voided,
                'deadline' : deadLine,
                'date' : date,
                'link' : infoLink
            }
            listingDict.append(ldict)
        return listingDict

    def TranslateFromMV(self, sentence:str) -> str:
        # Function to translate the Dhivehi contents to English. There is a cool down period implemented
        # so that Bing Translate doesn't get suspicous and prompt to enter a captcha.
        if self.lastTranslateTimeStamp != -1:
            if (time.time() - self.lastTranslateTimeStamp) < self.translateCooldownTime:
                time.sleep(self.translateCooldownTime - (time.time() - self.lastTranslateTimeStamp))
        self.lastTranslateTimeStamp = time.time()
        bresult = self.TranslateAgent.Translate(sentence, 'dv', 'en')
        return bresult[0]['translations'][0]['text']

    def ConvertDateToEnglish(self, date:str) -> str:
        # Convert the dates from Dhivehi to English
        fragments = date.split(' ')
        if len(fragments) == 4: return fragments[0] + ' ' + self.GetEnglishMonth(fragments[1]) + ' ' + fragments[2] + ', ' + fragments[3]
        else: return fragments[0] + ' ' + self.GetEnglishMonth(fragments[1]) + ' ' + fragments[2]

    def GetEnglishMonth(self, month:str) -> str:
        # Converts the months in Thaana to English. It is possible to use Bing Translate for this, but it is
        # more practical to use this because of the response time of the Bing Translate library
        match month:
            case 'ޖަނަވަރީ': return "January"
            case 'ފެބުރުވަރީ': return "February"
            case 'މާރިޗު': return "March"
            case 'އޭޕްރިލް': return "April"
            case 'މޭ': return "May"
            case 'ޖޫން': return "June"
            case 'ޖުލައި': return "July"
            case 'އޮގަސްޓް': return "August"
            case 'ސެޕްޓެންބަރު': return "September"
            case 'އޮކްޓޫބަރު': return "October"
            case 'ނޮވެންބަރު': return "November"
            case 'ޑިސެންބަރު': return "December"
            case _: return '??'
