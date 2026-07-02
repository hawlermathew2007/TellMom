# DefaultApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**ingestApiIngestPost**](DefaultApi.md#ingestapiingestpost) | **POST** /api/ingest | Ingest |
| [**listFlagsApiFlagsGet**](DefaultApi.md#listflagsapiflagsget) | **GET** /api/flags | List Flags |
| [**resolveFlagApiFlagsPlatformServerIdResolvePost**](DefaultApi.md#resolveflagapiflagsplatformserveridresolvepost) | **POST** /api/flags/{platform}/{server_id}/resolve | Resolve Flag |



## ingestApiIngestPost

> ingestApiIngestPost(ingestRequest)

Ingest

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { IngestApiIngestPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // IngestRequest
    ingestRequest: ...,
  } satisfies IngestApiIngestPostRequest;

  try {
    const data = await api.ingestApiIngestPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **ingestRequest** | [IngestRequest](IngestRequest.md) |  | |

### Return type

`void` (Empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **204** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listFlagsApiFlagsGet

> Array&lt;FlaggedConversation&gt; listFlagsApiFlagsGet(resolved)

List Flags

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ListFlagsApiFlagsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // boolean (optional)
    resolved: true,
  } satisfies ListFlagsApiFlagsGetRequest;

  try {
    const data = await api.listFlagsApiFlagsGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **resolved** | `boolean` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;FlaggedConversation&gt;**](FlaggedConversation.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## resolveFlagApiFlagsPlatformServerIdResolvePost

> { [key: string]: any; } resolveFlagApiFlagsPlatformServerIdResolvePost(platform, serverId)

Resolve Flag

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ResolveFlagApiFlagsPlatformServerIdResolvePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    platform: platform_example,
    // string
    serverId: serverId_example,
  } satisfies ResolveFlagApiFlagsPlatformServerIdResolvePostRequest;

  try {
    const data = await api.resolveFlagApiFlagsPlatformServerIdResolvePost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **platform** | `string` |  | [Defaults to `undefined`] |
| **serverId** | `string` |  | [Defaults to `undefined`] |

### Return type

**{ [key: string]: any; }**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

