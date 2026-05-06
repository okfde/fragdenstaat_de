FROM elasticsearch:8.19.3

RUN mkdir -p /usr/share/elasticsearch/config/analysis && curl -o /usr/share/elasticsearch/config/analysis/de_DR.xml "https://raw.githubusercontent.com/uschindler/german-decompounder/6227be052f4215294b5a5d498cdcdadfcf7196e6/de_DR.xml"
RUN mkdir -p /usr/share/elasticsearch/config/analysis && curl -o /usr/share/elasticsearch/config/analysis/dictionary-de.txt "https://raw.githubusercontent.com/uschindler/german-decompounder/6227be052f4215294b5a5d498cdcdadfcf7196e6/dictionary-de.txt"
