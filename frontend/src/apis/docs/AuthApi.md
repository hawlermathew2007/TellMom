# AuthApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getMeAuthMeGet**](AuthApi.md#getmeauthmeget) | **GET** /auth/me | Get Me |
| [**loginParentAuthLoginPost**](AuthApi.md#loginparentauthloginpost) | **POST** /auth/login | Login Parent |
| [**registerParentAuthRegisterPost**](AuthApi.md#registerparentauthregisterpost) | **POST** /auth/register | Register Parent |



## getMeAuthMeGet

> ParentResponse getMeAuthMeGet()

Get Me

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { GetMeAuthMeGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // Configure HTTP bearer authorization: HTTPBearer
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new AuthApi(config);

  try {
    const data = await api.getMeAuthMeGet();
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


## loginParentAuthLoginPost

> TokenResponse loginParentAuthLoginPost(parentLogin)

Login Parent

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { LoginParentAuthLoginPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  const body = {
    // ParentLogin
    parentLogin: ...,
  } satisfies LoginParentAuthLoginPostRequest;

  try {
    const data = await api.loginParentAuthLoginPost(body);
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


## registerParentAuthRegisterPost

> ParentResponse registerParentAuthRegisterPost(parentRegister)

Register Parent

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { RegisterParentAuthRegisterPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  const body = {
    // ParentRegister
    parentRegister: ...,
  } satisfies RegisterParentAuthRegisterPostRequest;

  try {
    const data = await api.registerParentAuthRegisterPost(body);
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

