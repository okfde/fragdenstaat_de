FROM docker.elastic.co/elasticsearch/elasticsearch:7.15.0

RUN mkdir -p /usr/share/elasticsearch/config/analysis && curl -o /usr/share/elasticsearch/config/analysis/de_DR.xml "https://raw.githubusercontent.com/uschindler/german-decompounder/master/de_DR.xml"
RUN mkdir -p /usr/share/elasticsearch/config/analysis && curl -o /usr/share/elasticsearch/config/analysis/dictionary-de.txt "https://raw.githubusercontent.com/uschindler/german-decompounder/master/dictionary-de.txt"
