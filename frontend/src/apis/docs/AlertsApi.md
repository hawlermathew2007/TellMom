# AlertsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**acknowledgeAlertApiAlertsAlertIdAcknowledgePost**](AlertsApi.md#acknowledgealertapialertsalertidacknowledgepost) | **POST** /api/alerts/{alert_id}/acknowledge | Acknowledge Alert |
| [**listAlertsApiAlertsGet**](AlertsApi.md#listalertsapialertsget) | **GET** /api/alerts | List Alerts |



## acknowledgeAlertApiAlertsAlertIdAcknowledgePost

> AlertResponse acknowledgeAlertApiAlertsAlertIdAcknowledgePost(alertId)

Acknowledge Alert

### Example

```ts
import {
  Configuration,
  AlertsApi,
} from '';
import type { AcknowledgeAlertApiAlertsAlertIdAcknowledgePostRequest } from '';

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
  } satisfies AcknowledgeAlertApiAlertsAlertIdAcknowledgePostRequest;

  try {
    const data = await api.acknowledgeAlertApiAlertsAlertIdAcknowledgePost(body);
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


## listAlertsApiAlertsGet

> Array&lt;AlertResponse&gt; listAlertsApiAlertsGet()

List Alerts

### Example

```ts
import {
  Configuration,
  AlertsApi,
} from '';
import type { ListAlertsApiAlertsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new AlertsApi(config);

  try {
    const data = await api.listAlertsApiAlertsGet();
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

