from modzy import ApiClient
from modzy.jobs import Jobs
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from typing import Any, List, Dict
import requests
import re
import time


# CONSTANTS
BASE_URL= "https://app.modzy.com/api"
JOB_TIMEOUT = 3600

# chrome driver settings
CHROMEDRIVER_LOCATION = './chromedriver/chromedriver.exe'
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-features=NetworkService")
options.add_argument("--window-size=1920x1080")
options.add_argument("--disable-features=VizDisplayCompositor")

# url validator
url_validator = re.compile(
                r'^(?:http)s?://' # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
                r'(?::\d+)?' # optional port
                r'(?:/?|[/?]\S+)$', 
                re.IGNORECASE
)



class Backend:
    def __init__(self, api_key):
        # init Modzy API Client
        self.client = ApiClient(base_url=BASE_URL, api_key=api_key)
        self.api_key = api_key
    
    def extract_text(self, search: Any) -> List[Dict]:
        # Extracting text
        extracted_contents = []
        if re.match(url_validator, search):
            # url
            r = requests.get(search)
            print(f"Response from extract_text GET requests: {r.status_code}")
            if r.status_code != 200:
                r.raise_for_status()       
            extracted_contents.append(r.content)
        else:
            # keyword
            urls = self.retrieve_top_n_news_url(search, n=3)
            if urls:
                for url in urls:
                    r = requests.get(url)
                    print(f"Response from extract_text GET requests: {r.status_code}")
                    if r.status_code != 200:
                        r.raise_for_status()       
                    extracted_contents.append(r.content)
            else:
                print(f"Retrievel urls: {urls}")
                raise Exception(f"No result is found based on the keyword")


        # Parsing title, published datetime, text via bs4
        news = []
        for content in extracted_contents:
            soup = BeautifulSoup(content, features='html.parser')
            title = soup.find('div', class_='at-headline').text
            published = soup.find('span', class_='dHSCiD').text
            text = ''.join([p.text for p in soup.findAll('div',class_='at-text')])
            # print(f"title: \n{tile}\n")
            # print(f"published: \n{published}"")
            # print(f"text: \n{text}")
            article = {
                'title': title,
                'published': published,
                'text': text
            }
            news.append(article)
        return news

  
    def retrieve_top_n_news_url(self, keyword, n: int = 3) -> List[Any]:
        with webdriver.Chrome(options=options) as driver:
            # load to coindesk keyword specified search page
            search_url = f"https://www.coindesk.com/search/?s={keyword}"
            driver.get(search_url)

            # maximize window and wait the page load
            driver.maximize_window()
            time.sleep(0.5)

            # Define CoinDesk sort-by element xpath 
            sort_by_xpath = '//*[@id="queryly_advanced_container"]/div[4]/div[1]/div[1]/div/div'
            by_newest_xpath = "/html/body/div[3]/div/div[2]/p[text()='By Newest']"
            sort_by_elem = driver.find_element_by_xpath(sort_by_xpath)

            # Emulate user clicking on sort-by button on CoinDesk webpage in order to sort result by newest
            action = ActionChains(driver)
            driver.execute_script("arguments[0].click();", sort_by_elem)
            action.move_to_element(sort_by_elem)
            by_newest_elem = driver.find_element_by_xpath(by_newest_xpath)
            action.move_to_element(by_newest_elem)
            action.perform()
            driver.execute_script("arguments[0].click();", by_newest_elem)

            # wait a while for search result sorting finish
            time.sleep(0.5)

            # Retrieve urls
            top_n_elements = driver.find_elements_by_xpath("//div[@class='searchstyles__SearchCard-ci5zlg-18 dLAdLq']/a")[1:n+1]
            urls = [elem.get_attribute("href") for elem in top_n_elements]
            return urls

        
    def summarize_text(self, text: List[str]) -> List[str]:
        # Add inputs
        sources = {}
        for i, t in enumerate(text):
            sources[f"input_{i+1}"] = {"input.txt": t}

        # submit the text summarization job
        print("running text summarization job...")
        job = self.client.jobs.submit_text("rs2qqwbjwb", "0.0.2", sources)
        print(f"job: {job}")

        # wait job complete
        job.block_until_complete(timeout=JOB_TIMEOUT)
        print("running text summarization job...DONE")

        # Retrieve summary if job status complete
        if job.status == Jobs.status.COMPLETED:
            result = job.get_result()
            summaries = []
            for key in sources:
                summary = result.get_source_outputs(key)['results.json']['summary']
                summaries.append(summary)
            return summaries
        else:
            raise Exception(f"Fail to retrieve summary output as the job ends with status {job.status}")


    def text_to_speech(self, text: List[str]) -> List[bytes]:
        # Add inputs
        sources = {}
        for i, t in enumerate(text):
            sources[f"input_{i+1}"] = {"input.txt": t}

        # submit text2speech job
        print("running text-to-speech job...")
        job = self.client.jobs.submit_text("uvdncymn6q", "0.0.3", sources)
        print(f"job: {job}")

        # wait job complete
        job.block_until_complete(timeout=JOB_TIMEOUT)
        print("running text-to-speech job...DONE")

        # Retrieve speech  if job status complete
        if job.status == Jobs.status.COMPLETED:
            result = job.get_result()
            headers = {
                'Accept': 'application/json', 
                'Authorization': f'ApiKey {self.api_key}'
            }
            speeches = []
            for key in sources:
                speechwav_url = result.get_source_outputs(key)['results.wav']
                speech_response =  requests.get(speechwav_url, headers=headers)
                if speech_response.status_code != 200:
                    speech_response.raise_for_status()
                speeches.append(speech_response.content)
            return speeches
        else:
            raise Exception(f"Fail to retrieve speech output as the job ends with status {job.status}")