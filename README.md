# `entsoe_cli`

[![build](https://github.com/paasim/entsoe_cli/workflows/build/badge.svg)](https://github.com/paasim/entsoe_cli/actions)

Python library for querying for data from [ENTSO-E transparency platform](https://transparencyplatform.zendesk.com/hc/en-us/articles/15692855254548-Sitemap-for-Restful-API-Integration). Currently only day-ahead energy prices for FI bidding zone are supported.

## usage

The usage requires a [security token](https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token). The following assume that the token is set in the environment variable `ENTSOE_TOKEN`:

```python
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from entsoe_cli import get_prices

FI = ZoneInfo("Europe/Helsinki")
start_time = datetime(2024, 11, 1, tzinfo=FI)
end_time = datetime(2024, 11, 15, tzinfo=FI)

prices = get_prices(start_time, end_time, token = os.environ.get("ENTSOE_TOKEN"))
for _ in range(5):
    print(next(prices))
```
