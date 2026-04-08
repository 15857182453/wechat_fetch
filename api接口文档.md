# API 接口文档

## 1. 公共请求参数

公共请求参数是指每个接口都需要使用到的请求参数。如下表所示的参数均放在 HTTP 请求的头部。

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| Authorization | string | 接口请求所需的认证码，即 Token，您可以在平台的 个人中心 > Token管理 中获取一个长期有效的 Token。请求时在 header 中增加“Authorization: Bearer {Token}” |
| language | string | 语言，默认 CH。可选：CH - 中文，US - 英文。 |

---

## 事件分析查询

### 1. 接口说明
获取指定事件分析的统计结果

### 2. 接口地址
```
https://api-portal.fenxiti.com/v1/api/projects/{spaceId}/analysis/olap_event/{id}/chartdata
```

### 3. 请求方式
GET

### 4. 公共请求参数
[公共请求参数](#1-公共请求参数)

### 5. 请求参数
| 名称 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| spaceId | string | 是 | 所在空间ID | WlGk4Daj |
| id | string | 是 | 分析单图标识符 | zqQR5MDo |

> 小贴士
> 您可以通过浏览器打开已保存的分析详情页，从 URL 中获取到空间ID 和分析单图标识符，例如：分析详情页的 URL 为
> https://api-portal.fenxiti.com/uba/spaces/WlGk4Daj/analysis/olap-event/AbQ3l3pY
> 其中 空间ID 为“WlGk4Daj“，分析单图标识符为”AbQ3l3pY“

### 6. 查询参数
| 名称 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| forceRefresh | boolean | 否 | 忽略缓存 | false |
| limit | int | 否 | 单次查询返回数据上限 | 最大 50,000，默认 1000 |
| offset | int | 否 | 查询标示位默认 0 | 0 |

### 7. 返回数据
paginationInfo 分页信息数据
| 名称 | 类型 | 描述 | 示例值 |
| --- | --- | --- | --- |
| offset | int | 查询标识位 | |
| limit | int | 单次查询返回数据上限 | |
| totalCount | int | 本次查询总计返回数据量 | |
| hasNextPage | boolean | 是否有下一页 | false：否 true：是 |
| hasPreviousPage | boolean | 是否有上一页 | false：否 true：是 |

analysisInfo 单图信息数据
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| name | String | 分析名称 |
| startTime | String | 开始事件 |
| endTime | String | 结束时间 |
| granularity | String | 时间粒度 |
| fetchedTime | Long | 数据查询时间 |

resultHeader 列名
resultRows 行数据

### 8. 示例
查询任意事件的图表信息

#### 请求示例
```bash
curl --location 'https://api-portal.fenxiti.com/v1/api/projects/WlGk4Daj/analysis/olap_event/AbQ3l3pY/chartdata?forceRefresh=false&offset=0&limit=1000' \
--header 'Authorization: Bearer ••••••'
```

#### 返回示例
```json
{
  "paginationInfo": {
    "offset": 0,
    "limit": 1000,
    "totalCount": 1,
    "hasNextPage": false,
    "hasPreviousPage": false
  },
  "analysisInfo": {
    "name": "事件分析API示例",
    "startTime": "2022-02-08 00:00:00",
    "endTime": "2022-03-10 00:00:00",
    "granularity": "DAY",
    "fetchedTime": "1646879291229"
  },
  "resultHeader": [
    "目标用户",
    "时间",
    "任意事件的总人数"
  ],
  "resultRows": [
    [
      "全部用户",
      "2022-02-28",
      "10"
    ]
  ]
}
```

---

## 漏斗分析查询

### 1. 接口说明
获取指定漏斗分析的统计结果

### 2. 接口地址
```
https://api-portal.fenxiti.com/v1/api/projects/{spaceId}/analysis/funnel/{id}/chartdata
```

### 3. 请求方式
GET

### 4. 公共请求参数
[公共请求参数](#1-公共请求参数)

### 5. 请求参数
| 名称 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| spaceId | String | 是 | 所在空间 ID | WlGk4Daj |
| id | String | 是 | 分析标识符 | zqQR5MDo |

> 小贴士
> 注：您可以通过浏览器打开已保存的分析详情页，从 URL 中获取到空间 ID 和分析标识符，例如：分析详情页的 URL 为
> https://api-portal.fenxiti.com/spaces/nxGK0Da6/analysis/funnel/J1GlMVDj
> 其中空间 ID 为“nxGK0Da6“，分析标识符为”J1GlMVDj“

### 6. 查询参数
| 名称 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| forceRefresh | boolean | 否 | 忽略缓存 | false |

### 7. 返回数据
analysisInfo 单图信息数据
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| name | String | 分析名称 |
| startTime | String | 开始事件 |
| endTime | String | 结束时间 |
| conversionWindow | int | 转化窗口期 |
| windowGranularity | String | 窗口期粒度 |
| fetchedTime | Long | 数据查询时间 |

resultHeader 列名
resultRows 行数据

### 8. 示例
查询访问到页面浏览的的转化信息

#### 请求示例
```bash
curl --location 'https://api-portal.fenxiti.com/v1/api/projects/nxGK0Da6/analysis/funnel/J1GlMVDj/chartdata?forceRefresh=false'  \
--header 'Authorization: Bearer ••••••'
```

#### 返回示例
```json
{
  "analysisInfo": {
    "name": "漏斗分析API示例",
    "startTime": "2022-03-03 00:00:00",
    "endTime": "2022-03-10 00:00:00",
    "conversionWindow": 1,
    "windowGranularity": "day",
    "fetchedTime": "1646879717428"
  },
  "resultHeader": [
    "时间",
    "总转化率",
    "访问",
    "第 1 步转化率",
    "访问"
  ],
  "resultRows": [
    [
      "全部",
      "0.0",
      "0.0",
      "0.0",
      "0.0"
    ],
    [
      "2022-03-03",
      "0",
      "0",
      "0",
      "0"
    ]
  ]
}
```

---

## 留存分析查询

### 1. 接口说明
获取指定留存分析的统计结果

### 2. 接口地址
```
https://api-portal.fenxiti.com/v1/api/projects/{spaceId}/analysis/retention/{id}/chartdata
```

### 3. 请求方式
GET

### 4. 公共请求参数
[公共请求参数](#1-公共请求参数)

### 5. 请求参数
| 名称 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| spaceId | String | 是 | 所在空间 ID | WlGk4Daj |
| id | String | 是 | 分析标识符 | zqQR5MDo |

> 小贴士
> 注：您可以通过浏览器打开已保存的分析详情页，从 URL 中获取到空间ID 和分析标识符，例如：分析详情页的 URL 为
> https://api-portal.fenxiti.com/spaces/nxGK0Da6/analysis/retention/wWDrYwGM
> 其中空间ID 为“nxGK0Da6“，分析标识符为”wWDrYwGM“

### 6. 查询参数
| 名称 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| forceRefresh | boolean | 否 | 忽略缓存 | false |

### 7. 返回数据
analysisInfo 单图信息数据
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| name | String | 分析名称 |
| startTime | String | 开始事件 |
| endTime | String | 结束时间 |
| granularity | String | 时间粒度 |
| fetchedTime | Long | 数据查询时间 |

resultHeader 列名
resultRows 行数据

### 8. 示例
查询任意行为到任意行为的的留存信息

#### 请求示例
```bash
curl --location 'https://api-portal.fenxiti.com/v1/api/projects/nxGK0Da6/analysis/retention/wWDrYwGM/chartdata?forceRefresh=false' \
--header 'Authorization: Bearer ••••••'
```

#### 返回示例
```json
{
  "analysisInfo": {
    "name": "留存分析API示例",
    "startTime": "2022-03-03 00:00:00",
    "endTime": "2022-03-10 00:00:00",
    "granularity": "day",
    "fetchedTime": "1646879808914"
  },
  "resultHeader": [
    "时间",
    "留存人数",
    "当日",
    "当日留存率",
    "次日",
    "次日留存率",
    "2日后",
    "2日后留存率",
    "3日后",
    "3日后留存率",
    "4日后",
    "4日后留存率",
    "5日后",
    "5日后留存率",
    "6日后",
    "6日后留存率"
  ],
  "resultRows": [
    [
      "全部",
      "0",
      "0",
      "0.0",
      "0",
      "0.0",
      "0",
      "0.0",
      "0",
      "0.0",
      "0",
      "0.0",
      "0",
      "0.0",
      "0",
      "0.0"
    ],
    [
      "2022-03-03",
      "0",
      "0",
      "0.0",
      "0",
      "0.0"
    ]
  ]
}
```

---

## 分布分析查询

### 1. 接口说明
获取指定分布分析的统计结果

### 2. 接口地址
```
https://api-portal.fenxiti.com/v1/api/projects/{spaceId}/analysis/frequency/{id}/chartdata
```

### 3. 请求方式
GET

### 4. 公共请求参数
[公共请求参数](#1-公共请求参数)

### 5. 请求参数
| 名称 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| spaceId | String | 是 | 所在空间 ID | WlGk4Daj |
| id | String | 是 | 分析标识符 | zqQR5MDo |

> 小贴士
> 注：您可以通过浏览器打开已保存分析详情页，从 URL 中获取到空间ID 和分析标识符，例如：分析详情页的 URL 为
> https://api-portal.fenxiti.com/spaces/nxGK0Da6/analysis/retention/wWDrYwGM
> 其中空间ID 为“nxGK0Da6“，分析标识符为”wWDrYwGM“

### 6. 查询参数
| 名称 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| forceRefresh | boolean | 否 | 忽略缓存 | false |

### 7. 返回数据
analysisInfo 单图信息数据
| 名称 | 类型 | 描述 |
| --- | --- | --- |
| name | String | 分析名称 |
| startTime | String | 开始事件 |
| endTime | String | 结束时间 |
| granularity | String | 时间粒度 |
| fetchedTime | Long | 数据查询时间 |

resultHeader 列名
resultRows 行数据

### 8. 示例
活跃天数指标在不同区间内的用户量分布

#### 请求示例
```bash
curl --location 'https://api-portal.fenxiti.com/v1/api/projects/nxGK0Da6/analysis/frequency/wWDrYwGM/chartdata?forceRefresh=false' \
--header 'Authorization: Bearer ••••••'
```

#### 返回示例
```json
{
  "analysisInfo": {
    "name": "分布分析API示例",
    "startTime": "2022-03-07 00:00:00",
    "endTime": "2022-03-10 00:00:00",
    "granularity": "",
    "fetchedTime": "1646880275623"
  },
  "resultHeader": [
    "活跃天数 区间范围",
    "用户量",
    "用户量占比"
  ],
  "resultRows": [
    [
      "[0.0,0.0]",
      "0",
      "0.0"
    ]
  ]
}
```

---

