
python 3.12
and requirements.txt

## Paper/Journal Parsing
Currently, the following conferences/journals are supported:
- CVF:
  - CVPR (starting 2013)
  - ICCV (starting 2013)
  - WACV (starting 2020)
- ECVA:
  - ECCV (starting 2018)
- PLMR:
  - ICML (starting 2020)
  - AISTATS (starting 2020)
  - CORL (starting 2020)
- BMVC (starting 2022)
- NIPS (all)*
- AAAI (starting 2020)*
- Openreview:
  - ICLR (starting 2020)
- IEEE (requires an API Key, register [here](https://developer.ieee.org/))
  - IROS (all - starting 1988)
  - ICRA (all - starting 1984)
  - TPAMI (all - starting 1979)

*Indicates that the request_limit in ```config.py``` might need to be decreased due to DDOS protections or timeouts.

While we do not support all years or all proceedings from each publisher by default, most classes are easily extendable for those requirements. The openreview API can be clunky due to inconsistent behaviour.

NOTE: The IEEE API allows 200 cals per day, where a single conference usually requires around 5-10 calls. Theoretically IEEE proceedings could be web-scraped, but it requires significant overhead.


feed parsing

the notifcations lack information such as a complete abstract or the full list of authors
can still be used but to make it more efficient we try to complete the information, atleast from large domains

information completing - using api keys is always more stable and quicker and therefore recommended
ieee
elsevier / sciencedirect - blocks normal requests; get an api key here https://dev.elsevier.com/
springer / nature
arxiv - api does not rquire an api key

elsevier api limits are quite high and should not be reached with normal use
if ieee and springer fails just rerun the parsing, the web based form is automatically selected as alternative


Thank you for arXiv for use of its open access interoperability.


