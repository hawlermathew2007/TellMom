# AuthApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getMeApiAuthMeGet**](AuthApi.md#getmeapiauthmeget) | **GET** /api/auth/me | Get Me |
| [**loginParentApiAuthLoginPost**](AuthApi.md#loginparentapiauthloginpost) | **POST** /api/auth/login | Login Parent |
| [**registerParentApiAuthRegisterPost**](AuthApi.md#registerparentapiauthregisterpost) | **POST** /api/auth/register | Register Parent |



## getMeApiAuthMeGet

> ParentResponse getMeApiAuthMeGet()

Get Me

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { GetMeApiAuthMeGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new AuthApi(config);

  try {
    const data = await api.getMeApiAuthMeGet();
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

[**ParentResponse**](ParentResponse.md)

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


## loginParentApiAuthLoginPost

> TokenResponse loginParentApiAuthLoginPost(parentLogin)

Login Parent

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { LoginParentApiAuthLoginPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  const body = {
    // ParentLogin
    parentLogin: ...,
  } satisfies LoginParentApiAuthLoginPostRequest;

  try {
    const data = await api.loginParentApiAuthLoginPost(body);
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
| **parentLogin** | [ParentLogin](ParentLogin.md) |  | |

### Return type

[**TokenResponse**](TokenResponse.md)

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


## registerParentApiAuthRegisterPost

> ParentResponse registerParentApiAuthRegisterPost(parentRegister)

Register Parent

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { RegisterParentApiAuthRegisterPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  const body = {
    // ParentRegister
    parentRegister: ...,
  } satisfies RegisterParentApiAuthRegisterPostRequest;

  try {
    const data = await api.registerParentApiAuthRegisterPost(body);
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
| **parentRegister** | [ParentRegister](ParentRegister.md) |  | |

### Return type

[**ParentResponse**](ParentResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **201** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

