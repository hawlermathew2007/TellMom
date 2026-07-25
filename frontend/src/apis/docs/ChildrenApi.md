# ChildrenApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createChildChildrenPost**](ChildrenApi.md#createchildchildrenpost) | **POST** /children | Create Child |
| [**deleteChildChildrenChildIdDelete**](ChildrenApi.md#deletechildchildrenchildiddelete) | **DELETE** /children/{child_id} | Delete Child |
| [**listChildrenChildrenGet**](ChildrenApi.md#listchildrenchildrenget) | **GET** /children | List Children |
| [**updateChildChildrenChildIdPut**](ChildrenApi.md#updatechildchildrenchildidput) | **PUT** /children/{child_id} | Update Child |



## createChildChildrenPost

> ChildAccountResponse createChildChildrenPost(childAccountCreate)

Create Child

### Example

```ts
import {
  Configuration,
  ChildrenApi,
} from '';
import type { CreateChildChildrenPostRequest } from '';

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
  } satisfies CreateChildChildrenPostRequest;

  try {
    const data = await api.createChildChildrenPost(body);
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


## deleteChildChildrenChildIdDelete

> deleteChildChildrenChildIdDelete(childId)

Delete Child

### Example

```ts
import {
  Configuration,
  ChildrenApi,
} from '';
import type { DeleteChildChildrenChildIdDeleteRequest } from '';

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
  } satisfies DeleteChildChildrenChildIdDeleteRequest;

  try {
    const data = await api.deleteChildChildrenChildIdDelete(body);
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


## listChildrenChildrenGet

> Array&lt;ChildAccountResponse&gt; listChildrenChildrenGet()

List Children

### Example

```ts
import {
  Configuration,
  ChildrenApi,
} from '';
import type { ListChildrenChildrenGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ChildrenApi(config);

  try {
    const data = await api.listChildrenChildrenGet();
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


## updateChildChildrenChildIdPut

> ChildAccountResponse updateChildChildrenChildIdPut(childId, childAccountUpdate)

Update Child

### Example

```ts
import {
  Configuration,
  ChildrenApi,
} from '';
import type { UpdateChildChildrenChildIdPutRequest } from '';

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
  } satisfies UpdateChildChildrenChildIdPutRequest;

  try {
    const data = await api.updateChildChildrenChildIdPut(body);
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

