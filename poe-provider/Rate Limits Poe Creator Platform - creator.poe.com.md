---
title: "Rate Limits | Poe Creator Platform"
source: "creator.poe.com"
url: "https://creator.poe.com/api-reference/rate-limits"
date_saved: "2026-04-13T19:30:06.909Z"
---

## Rate Limits

## Overview

The Poe API implements rate limiting to ensure fair usage and maintain service quality for all users. Understanding and properly handling these limits is essential for building robust integrations.

**Current Rate Limit:** 500 requests per minute (RPM)

Need Higher Limits?

---

## Rate Limit Headers

Every API response includes headers that help you track your current rate limit status:

| Header | Description | Example Value |
| --- | --- | --- |
| `x-ratelimit-limit-requests` | Maximum number of requests allowed per minute | `500` |
| `x-ratelimit-remaining-requests` | Number of requests remaining in the current window | `499` |
| `x-ratelimit-reset-requests` | Time in seconds until the rate limit window resets | `1` |

**Example Response Headers:**

```
< x-ratelimit-remaining-requests: 499
< x-ratelimit-limit-requests: 500
< x-ratelimit-reset-requests: 1
```

Monitor Your Usage

---

## Handling Rate Limits Gracefully

When your application exceeds the rate limit, the API will respond with a `429 Too Many Requests` status code. Implementing proper retry logic is essential for a robust integration.

### Watch for 429 Status Codes

Your application should always check for HTTP 429 responses and handle them appropriately rather than treating them as fatal errors.

Build Retry Logic

### Exponential Backoff Strategy

A basic technique for handling rate limits is to implement **exponential backoff** when you receive a 429 response:

1.  **Initial retry delay:** Start with a short delay (e.g., 1 second)
2.  **Increase exponentially:** Double the delay with each subsequent 429 (1s → 2s → 4s → 8s)
3.  **Add randomness (jitter):** Add random variation to prevent thundering herd effects
4.  **Set a maximum:** Cap the maximum retry delay to avoid indefinite waits

**Why add randomness?** If many clients hit the limit simultaneously and all retry at the same intervals, they'll create synchronized waves of traffic. Adding jitter (random delays) spreads out the retry attempts.

### Global Traffic Control

For more sophisticated applications, consider implementing rate limiting on the client side:

-   **Token bucket algorithm:** A proven approach for controlling request rates
-   **Global tracking:** Monitor rate limit consumption across all parts of your application
-   **Proactive throttling:** Reduce request volume when you detect you're approaching limits
-   **Circuit breaker pattern:** Temporarily stop requests when rate limits are consistently exceeded

Optimize Request Patterns

---

## Load Testing

If you're preparing for a major event or want to test your integration under load, follow these best practices:

### Mock Out API Requests

Build a configurable system for mocking Poe API requests during load tests. This allows you to:

-   Test your application's behavior at scale without consuming your rate limit
-   Avoid affecting production API availability
-   Simulate various response scenarios (including rate limit errors)

### Simulate Realistic Latency

For accurate load test results, simulate network latency in your mocked responses:

1.  **Sample real API calls:** Measure actual response times from live Poe API requests
2.  **Apply delays:** Use these measurements to add realistic sleep times to your mocked responses
3.  **Vary the delays:** Use a distribution of latency values rather than a fixed delay

This approach ensures your load tests reflect real-world performance characteristics.

Don't Load Test Production

---

## Usage Tracking

### Usage API

If you need detailed information about your API usage, including a log of all your API calls, use the **Usage API**.

The Usage API provides:

-   Historical usage data
-   Request counts and patterns
-   Point consumption tracking
-   Detailed call logs

---

## Best Practices Summary

-   ✅ **Monitor rate limit headers** in every response
-   ✅ **Implement exponential backoff** with jitter for 429 responses
-   ✅ **Add client-side rate limiting** for high-volume applications
-   ✅ **Cache responses** where appropriate to reduce API calls
-   ✅ **Use mocked endpoints** for load testing
-   ✅ **Track usage** with the Usage API to understand your patterns
-   ❌ **Never ignore 429 errors** - always retry with backoff
-   ❌ **Don't retry immediately** - respect the rate limit reset time
-   ❌ **Don't load test production** - use mocks instead

Contact Us