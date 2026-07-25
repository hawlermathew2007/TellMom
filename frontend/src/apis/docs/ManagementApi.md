# ManagementApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**connectManagementConnectPost**](ManagementApi.md#connectmanagementconnectpost) | **POST** /management/connect | Connect |
| [**getStateManagementStateGet**](ManagementApi.md#getstatemanagementstateget) | **GET** /management/state | Get State |
| [**loginManagementLoginPost**](ManagementApi.md#loginmanagementloginpost) | **POST** /management/login | Login |
| [**registerManagementRegisterPost**](ManagementApi.md#registermanagementregisterpost) | **POST** /management/register | Register |
| [**renewPasscodeManagementRenewPasscodePost**](ManagementApi.md#renewpasscodemanagementrenewpasscodepost) | **POST** /management/renew_passcode | Renew Passcode |
| [**statusManagementStatusGet**](ManagementApi.md#statusmanagementstatusget) | **GET** /management/status | Status |
| [**updateStateManagementStatePost**](ManagementApi.md#updatestatemanagementstatepost) | **POST** /management/state | Update State |



## connectManagementConnectPost

> any connectManagementConnectPost()

Connect

### Example

```ts
import {
  Configuration,
  ManagementApi,
} from '';
import type { ConnectManagementConnectPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ManagementApi();

  try {
    const data = await api.connectManagementConnectPost();
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

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getStateManagementStateGet

> any getStateManagementStateGet()

Get State

### Example

```ts
import {
  Configuration,
  ManagementApi,
} from '';
import type { GetStateManagementStateGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ManagementApi();

  try {
    const data = await api.getStateManagementStateGet();
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

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## loginManagementLoginPost

> any loginManagementLoginPost()

Login

### Example

```ts
import {
  Configuration,
  ManagementApi,
} from '';
import type { LoginManagementLoginPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ManagementApi();

  try {
    const data = await api.loginManagementLoginPost();
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

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## registerManagementRegisterPost

> any registerManagementRegisterPost()

Register

### Example

```ts
import {
  Configuration,
  ManagementApi,
} from '';
import type { RegisterManagementRegisterPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ManagementApi();

  try {
    const data = await api.registerManagementRegisterPost();
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

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## renewPasscodeManagementRenewPasscodePost

> any renewPasscodeManagementRenewPasscodePost()

Renew Passcode

### Example

```ts
import {
  Configuration,
  ManagementApi,
} from '';
import type { RenewPasscodeManagementRenewPasscodePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ManagementApi();

  try {
    const data = await api.renewPasscodeManagementRenewPasscodePost();
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

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## statusManagementStatusGet

> any statusManagementStatusGet()

Status

### Example

```ts
import {
  Configuration,
  ManagementApi,
} from '';
import type { StatusManagementStatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ManagementApi();

  try {
    const data = await api.statusManagementStatusGet();
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

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## updateStateManagementStatePost

> any updateStateManagementStatePost(configUpdate)

Update State

### Example

```ts
import {
  Configuration,
  ManagementApi,
} from '';
import type { UpdateStateManagementStatePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ManagementApi();

  const body = {
    // ConfigUpdate
    configUpdate: ...,
  } satisfies UpdateStateManagementStatePostRequest;

  try {
    const data = await api.updateStateManagementStatePost(body);
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
| **configUpdate** | [ConfigUpdate](ConfigUpdate.md) |  | |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

