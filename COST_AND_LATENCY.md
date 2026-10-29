# Cost and Latency Note

## API-call estimate
There are 8 posts in the sample `jobs.csv`. The program makes one successful API call per post in the normal case: **about 8 calls for one full run**. If a reply fails validation or the API errors, it retries once. Worst case for these 8 posts is **16 calls**, followed by local fallback.

## Latency
The code uses a 45-second HTTP timeout per call. Actual response time depends on the model, network, and provider load; it is not guaranteed. For planning only, estimate roughly 1–5 seconds per successful call under ordinary conditions, so 8 calls may take about 8–40 seconds, excluding retries and network delays. Record actual timings during your live demo.

## Cost
No fixed price is claimed here because API pricing and the model can change, and cost depends on prompt and response token counts. Estimate using:

`daily cost = (input tokens / 1,000,000 × current input price) + (output tokens / 1,000,000 × current output price)`

For this small dataset, count tokens from an actual run and multiply by the provider's current published model prices. If using a free-tier allowance, actual billed cost may be zero within that allowance. Do not put the API key in the code or GitHub.
