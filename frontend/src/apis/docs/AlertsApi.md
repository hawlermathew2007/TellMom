# AlertsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**acknowledgeAlertAlertsAlertIdAcknowledgePost**](AlertsApi.md#acknowledgealertalertsalertidacknowledgepost) | **POST** /alerts/{alert_id}/acknowledge | Acknowledge Alert |
| [**getGroomingAnalysisAlertsAlertIdAnalysisGet**](AlertsApi.md#getgroominganalysisalertsalertidanalysisget) | **GET** /alerts/{alert_id}/analysis | Get Grooming Analysis |
| [**listAlertsAlertsGet**](AlertsApi.md#listalertsalertsget) | **GET** /alerts | List Alerts |



## acknowledgeAlertAlertsAlertIdAcknowledgePost

> AlertResponse acknowledgeAlertAlertsAlertIdAcknowledgePost(alertId)

Acknowledge Alert

### Example

```ts
import {
  Configuration,
  AlertsApi,
} from '';
import type { AcknowledgeAlertAlertsAlertIdAcknowledgePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new AlertsApi(config);

  const body = {
    // number
    alertId: 56,
  } satisfies AcknowledgeAlertAlertsAlertIdAcknowledgePostRequest;

  try {
    const data = await api.acknowledgeAlertAlertsAlertIdAcknowledgePost(body);
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
| **alertId** | `number` |  | [Defaults to `undefined`] |

### Return type

[**AlertResponse**](AlertResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getGroomingAnalysisAlertsAlertIdAnalysisGet

> IncrementalAnalysisResponse getGroomingAnalysisAlertsAlertIdAnalysisGet(alertId)

Get Grooming Analysis

Get or generate incremental grooming analysis for an alert.  Returns only newly detected stages (empty if none detected or already fully analyzed).

### Example

```ts
import {
  Configuration,
  AlertsApi,
} from '';
import type { GetGroomingAnalysisAlertsAlertIdAnalysisGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new AlertsApi(config);

  const body = {
    // number
    alertId: 56,
  } satisfies GetGroomingAnalysisAlertsAlertIdAnalysisGetRequest;

  try {
    const data = await api.getGroomingAnalysisAlertsAlertIdAnalysisGet(body);
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
| **alertId** | `number` |  | [Defaults to `undefined`] |

### Return type

[**IncrementalAnalysisResponse**](IncrementalAnalysisResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listAlertsAlertsGet

> Array&lt;AlertResponse&gt; listAlertsAlertsGet()

List Alerts

### Example

```ts
import {
  Configuration,
  AlertsApi,
} from '';
import type { ListAlertsAlertsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new AlertsApi(config);

  try {
    const data = await api.listAlertsAlertsGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Array&lt;AlertResponse&gt;**](AlertResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

