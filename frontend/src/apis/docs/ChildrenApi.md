# ChildrenApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createChildApiChildrenPost**](ChildrenApi.md#createchildapichildrenpost) | **POST** /api/children | Create Child |
| [**deleteChildApiChildrenChildIdDelete**](ChildrenApi.md#deletechildapichildrenchildiddelete) | **DELETE** /api/children/{child_id} | Delete Child |
| [**listChildrenApiChildrenGet**](ChildrenApi.md#listchildrenapichildrenget) | **GET** /api/children | List Children |
| [**updateChildApiChildrenChildIdPut**](ChildrenApi.md#updatechildapichildrenchildidput) | **PUT** /api/children/{child_id} | Update Child |



## createChildApiChildrenPost

> ChildAccountResponse createChildApiChildrenPost(childAccountCreate)

Create Child

### Example

```ts
import {
  Configuration,
  ChildrenApi,
} from '';
import type { CreateChildApiChildrenPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ChildrenApi(config);

  const body = {
    // ChildAccountCreate
    childAccountCreate: ...,
  } satisfies CreateChildApiChildrenPostRequest;

  try {
    const data = await api.createChildApiChildrenPost(body);
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
| **childAccountCreate** | [ChildAccountCreate](ChildAccountCreate.md) |  | |

### Return type

[**ChildAccountResponse**](ChildAccountResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **201** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## deleteChildApiChildrenChildIdDelete

> deleteChildApiChildrenChildIdDelete(childId)

Delete Child

### Example

```ts
import {
  Configuration,
  ChildrenApi,
} from '';
import type { DeleteChildApiChildrenChildIdDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ChildrenApi(config);

  const body = {
    // number
    childId: 56,
  } satisfies DeleteChildApiChildrenChildIdDeleteRequest;

  try {
    const data = await api.deleteChildApiChildrenChildIdDelete(body);
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
| **childId** | `number` |  | [Defaults to `undefined`] |

### Return type

`void` (Empty response body)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **204** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listChildrenApiChildrenGet

> Array&lt;ChildAccountResponse&gt; listChildrenApiChildrenGet()

List Children

### Example

```ts
import {
  Configuration,
  ChildrenApi,
} from '';
import type { ListChildrenApiChildrenGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ChildrenApi(config);

  try {
    const data = await api.listChildrenApiChildrenGet();
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

[**Array&lt;ChildAccountResponse&gt;**](ChildAccountResponse.md)

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


## updateChildApiChildrenChildIdPut

> ChildAccountResponse updateChildApiChildrenChildIdPut(childId, childAccountUpdate)

Update Child

### Example

```ts
import {
  Configuration,
  ChildrenApi,
} from '';
import type { UpdateChildApiChildrenChildIdPutRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ChildrenApi(config);

  const body = {
    // number
    childId: 56,
    // ChildAccountUpdate
    childAccountUpdate: ...,
  } satisfies UpdateChildApiChildrenChildIdPutRequest;

  try {
    const data = await api.updateChildApiChildrenChildIdPut(body);
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
| **childId** | `number` |  | [Defaults to `undefined`] |
| **childAccountUpdate** | [ChildAccountUpdate](ChildAccountUpdate.md) |  | |

### Return type

[**ChildAccountResponse**](ChildAccountResponse.md)

### Authorization

[HTTPBearer](../README.md#HTTPBearer)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

