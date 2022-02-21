import requests
import re
import nltk
import json
import time
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from gensim.parsing.preprocessing import strip_tags


nltk.download("wordnet")
nltk.download("punkt")
nltk.download('averaged_perceptron_tagger')


# Headers for the BeautifulSoup 
headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9'}


class Article:

    def __init__(self, title="", abstract="", publish_year="", url="", referenceCount="", citationCount="", influentialCitationCount=""):
        self.title = title

        self.abstract = abstract

        self.publish_year = publish_year

        self.url = url

        self.referenceCount = referenceCount

        self.citationCount = citationCount

        self.influentialCitationCount = influentialCitationCount


    def __str__(self):
        tokenized_abstract = self.abstract.split()
        abs_part1 = " ".join(tokenized_abstract[0:10])
        abs_part2 = " ".join(tokenized_abstract[-10:])

        return ("Title: {}\nAbstract: {} ... {}\nYear: {}\nURL: {}".format(self.title, abs_part1, abs_part2, self.publish_year, self.url))


class WebScrapper:

    def __init__(self, search_words=[]):
        '''
        Creation of object WebScrapper. The articles atribute aggregates
        all the articles fetched from the following methods.
        '''
        if len(search_words) >= 1:
            self.search_words = search_words
        else:
            raise Exception("Attribute Error! Please place at least one element in search_words.")

        self.articles = []


    def read_from_Excel(self, path="fetched_data.xlsx"):
        '''
        Read articles components from an Microsoft Excel file 
        and add them to the atribute articles of the WebScrapper
        object
        Return the number of articles read
        '''
        df = pd.read_excel(path)

        df.dropna(subset=["Abstract"], inplace=True)

        titles = list(df["Title"])
        abstracts = list(df["Abstract"])
        publish_years = list(df["Publish Year"])
        urls = list(df["URL"])
        referenceCount = list(df["referenceCount"])
        citationCount = list(df["citationCount"])
        influentialCitationCount = list(df["influentialCitationCount"])

        self.articles = []
        for i in range(0,len(titles)):
            self.articles.append(Article(title=titles[i], abstract=abstracts[i], publish_year=publish_years[i], url=urls[i],
                                         referenceCount=referenceCount[i], citationCount=citationCount[i],
                                         influentialCitationCount=influentialCitationCount[i]))

        return i


    def __soupify(self, url):
        ''' 
        Create a BeautifulSop object of a certain url
        '''
        response = requests.get(url, headers=headers)
        return BeautifulSoup(response.content, "lxml")


    def removeHTMLTags(self, html_block):
        '''
        Remove all of the html tags of a
        html block of code utilizing regular
        expressions
        '''
        return re.sub(r'<.*?>', "", str(html_block))


    def save_to_excel(self, name="output.xlsx"):
        '''
        Save fetched articles components to a Microsoft
        Excel file
        '''
        data = []
        for article in self.articles:
            data.append(article.toExcel())

        df = pd.DataFrame(data)

        df.to_excel(excel_writer=name, sheet_name="Articles", header=["Title", "Abstract", "Publish Year", "URL", "referenceCount", "citationCount", "influentialCitationCount"])    


    def fetchArticles(self, max_articles=100):
        '''
        Start the fetching process of article components
        using both Springer and PubMed web scraping methods
        '''
        self.fetchSpringerArticles(max_articles)
        self.fetchPubMedArticles(max_articles)

        self.removeInvalid()


    def removeInvalid(self):
        ''' 
        Remove invalid articles from the article list such as
        equal articles or some know errors when fetching certain
        article components
        '''
        for article1 in self.articles:
            for i, article2 in enumerate(self.articles):
                if article2.title == article1.title:
                   self.articles.pop(i)

        for i, article in enumerate(self.articles):
            if article.publish_year == "http" or article.abstract == "":
                self.articles.pop(i)


    def fetchSpringerArticles(self, max_articles=250):
        '''
        Fetch article components from Springer
        '''
        words_query = "+".join(self.search_words)

        springer_url_init = "https://link.springer.com/"

        articles_url = []
        num_articles = 0
        page = 1

        while (num_articles < max_articles):

            stop_cycle = False

            springer_url = "https://link.springer.com/search/page/{}?facet-content-type=%22Article%22&query={}".format(page, words_query)
            soup = self.__soupify(springer_url)

            if page == 1:
                aux = self.removeHTMLTags(soup.find_all("strong")[0]).split(",")

                # Springer represents their numbers above 1,000 with a comma
                # The comma need to be removed and then converted to integer
                if len(aux) > 1:
                    num_articles_found = int(aux[0]+aux[1])
                else:
                    num_articles_found = int(aux[0])

                print("num_articles_found = {}".format(num_articles_found))
                
                if max_articles > num_articles_found:
                    max_articles = num_articles_found
                    print("Maximum number of articles found is {}".format(num_articles_found))  

            # Get URL of articles
            a_tags = soup.find_all("a", attrs={"class", "title"})
            for item in a_tags:
                articles_url.append(springer_url_init+item["href"])
                num_articles += 1

                # If number of articles collected reaches de maximum number
                if num_articles >= max_articles:
                    stop_cycle = True
                    break
        
            # Stop the article URL collection
            if stop_cycle:
                break

            # New page
            page += 1

        # Web scraping of title, abstract, and publish year 
        titles = []
        abstracts = []
        publish_years = []
        sucessful_urls = []

        # Variable to check if something was found by the web scraping method
        sucessful_retrieved = False

        for url in articles_url:
            soup = self.__soupify(url)

            try:
                title_temp = self.removeHTMLTags(soup.find_all("h1", attrs={"class", "c-article-title"})[0])  
                titles.append((title_temp.replace("\n","")).strip())
                sucessful_retrieved = True
            except Exception as e:
                titles.append("")
                print("Error fetching title of {}".format(url))

            try:
                abstract_temp = self.removeHTMLTags(soup.find_all("div", attrs={"class", "c-article-section"})[0])
                abstract_temp_2 = (abstract_temp.replace("\n","")).strip()
                if abstract_temp_2[0:8] == "Abstract":
                    abstracts.append(abstract_temp_2[8:-1])
                elif abstract_temp_2[0:9] == "Refereces":
                    abstract_temp_2.append("")
                else:
                    abstracts.append(abstract_temp_2)
                sucessful_retrieved = True
            except Exception as e:
                abstracts.append("")
                print("Error fetching abstract of {}".format(url))

            try:
                publish_year_temp = self.removeHTMLTags(soup.find_all("span", attrs={"class", "c-bibliographic-information__value"}))
                publish_year_temp_2 = publish_year_temp.split()[2][0:4]   
                if publish_year_temp_2 != "http":
                    publish_years.append(publish_year_temp_2)
                else:
                    publish_years.append("")
                sucessful_retrieved = True
            except Exception as e:
                publish_years.append("")
                print("Error fetching published year of {}".format(url))

            if sucessful_retrieved:
                sucessful_urls.append(url)
                
            sucessful_retrieved = False

        # Add to the articles list
        for ind in range(0, len(titles)):
            self.articles.append(Article(title=titles[ind], abstract=abstracts[ind], publish_year=publish_years[ind], url=sucessful_urls[ind]))
        

    def fetchPubMedArticles(self, max_articles=250):
        '''
        Fetch article components from PubMed
        '''
        words_query = "%20".join(self.search_words)

        articles_url = []

        num_articles = 0
        page = 0

        while (num_articles < max_articles):

            stop_cycle = False

            if page == 1:
                pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/?term={}".format(words_query, page)

                soup = self.__soupify(pubmed_url)

                num_articles_found = int(self.removeHTMLTags(soup.find_all("span", attrs={"class", "value"})[0]))

                if max_articles > num_articles_found:
                    max_articles = num_articles_found
                    print("Maximum number of articles found is {}".format(num_articles_found))  

            else:
                pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/?term={}&page={}".format(words_query, page)

                soup = self.__soupify(pubmed_url)

            # Get URL of articles
            a_tags = soup.find_all("a", attrs={"class", "docsum-title"})
            for item in a_tags:
                articles_url.append("https://pubmed.ncbi.nlm.nih.gov/"+item["href"])
                num_articles += 1

                # If number of articles collected reaches de maximum number
                if num_articles >= max_articles:
                    stop_cycle = True
                    break
        
            # Stop the article URL collection
            if stop_cycle:
                break

            # Next page
            page += 1            

        # Web scraping of title, abstract, and publish year          
        titles = []
        abstracts = []
        publish_years = []
        sucessful_urls = []

        # Variable to check if something was found by the web scraping method
        sucessful_retrieved = False

        for url in articles_url:
            soup = self.__soupify(url)

            try:
                title_temp = self.removeHTMLTags(soup.find_all("h1", attrs={"class", "heading-title"})[0])
                titles.append((title_temp.replace("\n","")).strip())
                sucessful_retrieved = True
            except Exception as e:
                titles.append("")
                print("Error fetching title of {}".format(url))

            try:
                abstract_temp = self.removeHTMLTags(soup.find_all("div", attrs={"class", "abstract-content selected"})[0])    
                abstracts.append((abstract_temp.replace("\n","")).strip())
                sucessful_retrieved = True
            except Exception as e:
                abstracts.append("")
                print("Error fetching abstract of {}".format(url))

            try:    
                publish_year_string = self.removeHTMLTags(soup.find_all("span", attrs={"class", "cit"})[0])
                publish_years.append(publish_year_string.split()[0][0:4])                
                sucessful_retrieved = True
            except Exception as e:
                publish_years.append("")
                print("Error fetching published year of {}".format(url))

            if sucessful_retrieved:
                sucessful_urls.append(url)
                
            sucessful_retrieved = False

        # Add to the articles list
        for ind in range(0, len(titles)):
            self.articles.append(Article(title=titles[ind], abstract=abstracts[ind], publish_year=publish_years[ind], url=sucessful_urls[ind]))    


    def fetchSemanticScholar(self, max_articles=100, start=0):

        words_query = "+".join(self.search_words)

        offset = start
        num_articles = 0

        while (num_articles <= max_articles):
            
            stop_function = False

            url = "https://api.semanticscholar.org/graph/v1/paper/search?query={}&offset={}&limit=20&fields=url,title,abstract,year,referenceCount,citationCount,influentialCitationCount".format(words_query, offset)

            soup = self.__soupify(url)

            results = self.removeHTMLTags(str(soup))

            try:
                dic = json.loads(results)
            except Exception as e:
                print("Error converting data to dictionary")

            num_articles_found = dic["total"]
            if max_articles > num_articles_found:
                max_articles = num_articles_found
                print("Maximum number of articles found is {}".format(num_articles_found))  


            print("max_articles = {}".format(max_articles))

            for article in dic["data"]:
                try:
                    self.articles.append(Article(title=article["title"], abstract=article["abstract"], 
                                                publish_year=article["year"], url=article["url"], referenceCount=article["referenceCount"],
                                                citationCount=article["citationCount"], influentialCitationCount=article["influentialCitationCount"]))
                    
                    num_articles += 1

                    if num_articles == max_articles:
                        stop_function = True
                        break
                
                except Exception as e:
                    print("Error while adding the article number {}".format(num_articles))

            if stop_function:
                print("{} articles added".format(num_articles))
                return

            offset = dic["next"]

            print("{} articles added".format(num_articles))
            # Wait 1 minute
            time.sleep(60)
