# StackSense catalog

This file is generated from `stacksense/kb.py`. Do not edit it by hand.
Scores run from 1 (weak or easy, depending on the column) to 5.
`ops` is burden: 1 is easy. `lock` is lock-in: 1 is portable.

## Frontend

| name | id | seo | interact | complexity | ops | low end | sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Astro | astro | 5 | 2 | 2 | 1 | 5 | https://docs.astro.build/ |
| Eleventy | eleventy | 5 | 1 | 2 | 1 | 5 | https://www.11ty.dev/docs/ |
| Next.js | nextjs | 5 | 5 | 3 | 2 | 3 | https://nextjs.org/docs, https://react.dev/learn/creating-a-react-app |
| Nuxt | nuxt | 5 | 4 | 3 | 2 | 3 | https://nuxt.com/docs |
| SvelteKit | sveltekit | 5 | 4 | 3 | 2 | 4 | https://svelte.dev/docs/kit |
| React (Vite) | react_vite | 2 | 5 | 2 | 2 | 3 | https://react.dev/learn/creating-a-react-app, https://vite.dev/guide/, https://react.dev/blog/2025/02/14/sunsetting-create-react-app |
| Angular | angular | 2 | 4 | 4 | 2 | 2 | https://angular.dev/ |
| ASP.NET Core Razor Pages | razor_pages | 4 | 3 | 2 | 2 | 4 | https://learn.microsoft.com/aspnet/core/razor-pages/, https://dotnet.microsoft.com/platform/support/policy/dotnet-core |
| Blazor | blazor | 2 | 4 | 3 | 2 | 3 | https://dotnet.microsoft.com/apps/aspnet/web-apps/blazor, https://dotnet.microsoft.com/platform/support/policy/dotnet-core |
| htmx with server templates | htmx | 4 | 3 | 2 | 1 | 5 | https://htmx.org/docs/ |
| Expo (React Native) | expo | 1 | 4 | 3 | 2 | 3 | https://docs.expo.dev/, https://docs.expo.dev/versions/latest/sdk/sqlite/ |
| Flutter | flutter | 1 | 4 | 3 | 2 | 3 | https://docs.flutter.dev/ |
| Compose Multiplatform | compose_mp | 1 | 4 | 4 | 2 | 4 | https://www.jetbrains.com/compose-multiplatform/, https://developer.android.com/kotlin |
| Kotlin and Jetpack Compose | kotlin_android | 1 | 4 | 3 | 2 | 5 | https://developer.android.com/kotlin |
| SwiftUI | swiftui | 1 | 4 | 3 | 2 | 4 | https://developer.apple.com/xcode/swiftui/ |
| Electron | electron | 1 | 4 | 3 | 2 | 2 | https://www.electronjs.org/docs/latest |
| Tauri | tauri | 1 | 4 | 4 | 3 | 4 | https://v2.tauri.app/ |

## Backend

| name | id | perf | complexity | ops | user ceiling | sources |
| --- | --- | --- | --- | --- | --- | --- |
| NestJS | nestjs | 3 | 3 | 2 | 2000000 | https://docs.nestjs.com/ |
| Fastify | fastify | 4 | 2 | 2 | 2000000 | https://fastify.dev/docs/latest/ |
| FastAPI | fastapi | 4 | 2 | 2 | 1000000 | https://fastapi.tiangolo.com/ |
| Django | django | 3 | 3 | 2 | 1000000 | https://docs.djangoproject.com/ |
| Spring Boot | spring_boot | 4 | 4 | 3 | 10000000 | https://spring.io/projects/spring-boot |
| ASP.NET Core (.NET 10) | aspnet | 5 | 3 | 2 | 5000000 | https://learn.microsoft.com/aspnet/core/, https://dotnet.microsoft.com/platform/support/policy/dotnet-core |
| Laravel | laravel | 3 | 2 | 2 | 1000000 | https://laravel.com/docs |
| Ruby on Rails | rails | 3 | 3 | 2 | 1000000 | https://rubyonrails.org/ |
| Go (net/http) | go_http | 5 | 3 | 2 | 10000000 | https://go.dev/doc/, https://github.com/go-chi/chi, https://github.com/coder/websocket |
| PocketBase | pocketbase | 3 | 1 | 1 | 20000 | https://pocketbase.io/docs/ |
| Cloudflare Workers | workers | 4 | 2 | 1 | 50000 | https://developers.cloudflare.com/workers/ |

## Database

| name | id | acid | cost tier | lock | user ceiling | sources |
| --- | --- | --- | --- | --- | --- | --- |
| PostgreSQL | postgresql | True | 1 | 1 | 10000000 | https://www.postgresql.org/docs/current/, https://www.digitalocean.com/pricing/managed-databases |
| MySQL | mysql | True | 1 | 1 | 5000000 | https://dev.mysql.com/doc/ |
| Microsoft SQL Server | sqlserver | True | 2 | 3 | 5000000 | https://learn.microsoft.com/lifecycle/products/sql-server-2019 |
| Azure SQL Database | azure_sql | True | 2 | 3 | 5000000 | https://learn.microsoft.com/azure/azure-sql/ |
| MongoDB | mongodb | False | 2 | 3 | 5000000 | https://www.mongodb.com/docs/manual/, https://www.mongodb.com/docs/atlas/app-services/sync/device-sync-deprecation/ |
| SQLite | sqlite | True | 0 | 1 | 5000 | https://www.sqlite.org/docs.html |
| Amazon DynamoDB | dynamodb | False | 2 | 5 | 50000000 | https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ |
| CockroachDB | cockroach | True | 3 | 2 | 20000000 | https://www.cockroachlabs.com/docs/stable/ |
| Cloud Firestore | firestore | False | 1 | 5 | 5000000 | https://firebase.google.com/docs/firestore, https://firebase.google.com/support/dynamic-links-faq |
| Cloudflare D1 | d1 | True | 0 | 4 | 20000 | https://developers.cloudflare.com/d1/ |
| ClickHouse | clickhouse | False | 2 | 2 | 50000000 | https://clickhouse.com/docs |

## Hosting

| name | id | kind | ops | baa | cost tier | socket ceiling | sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cloudflare Pages | cloudflare_pages | static | 1 | False | 0 | 0 | https://developers.cloudflare.com/pages/ |
| GitHub Pages | github_pages | static | 1 | False | 0 | 0 | https://docs.github.com/pages |
| Netlify | netlify | static | 1 | False | 1 | 50 | https://docs.netlify.com/ |
| Vercel | vercel | app | 1 | False | 1 | 800 | https://vercel.com/docs |
| Amazon ECS on Fargate | aws_ecs | app | 4 | True | 2 | 200000 | https://docs.aws.amazon.com/AmazonECS/latest/developerguide/, https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html, https://docs.aws.amazon.com/eks/latest/userguide/ |
| AWS Lambda | aws_lambda | serverless | 2 | True | 1 | 20000 | https://docs.aws.amazon.com/lambda/latest/dg/, https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html |
| Google Cloud Run | gcp_run | app | 3 | True | 2 | 50000 | https://cloud.google.com/run/docs |
| Azure App Service | azure_appservice | app | 2 | True | 2 | 50000 | https://learn.microsoft.com/azure/app-service/ |
| DigitalOcean App Platform | do_app | app | 2 | False | 1 | 3000 | https://docs.digitalocean.com/products/app-platform/, https://docs.digitalocean.com/platform/regional-availability/, https://www.digitalocean.com/pricing/managed-databases |
| DigitalOcean Droplet | do_droplet | vm | 4 | False | 1 | 3000 | https://docs.digitalocean.com/platform/regional-availability/ |
| Amazon EC2 | aws_ec2 | vm | 4 | True | 2 | 200000 | https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html |
| Compute Engine | gcp_vm | vm | 4 | True | 2 | 200000 | https://cloud.google.com/run/docs |
| Azure Virtual Machines | azure_vm | vm | 4 | True | 2 | 200000 | https://learn.microsoft.com/azure/app-service/ |
| Docker Compose on your own machines | docker_compose | vm | 4 | True | 1 | 5000 | https://docs.docker.com/compose/ |
| Cloudflare Workers | workers | serverless | 1 | False | 0 | 300 | https://developers.cloudflare.com/workers/, https://developers.cloudflare.com/d1/ |
| Amazon EKS | aws_eks | app | 5 | True | 3 | 500000 | https://docs.aws.amazon.com/eks/latest/userguide/ |

## Retired products the engine will not recommend

| name | severity | note | source |
| --- | --- | --- | --- |
| AngularJS | critical | AngularJS reached end of life on 31 December 2021. | https://angularjs.org/ |
| Create React App | warning | Create React App was deprecated for new apps on 14 February 2025. | https://react.dev/blog/2025/02/14/sunsetting-create-react-app |
| SQL Server 2008 | critical | SQL Server 2008 is long past extended support. | https://learn.microsoft.com/lifecycle/products/microsoft-sql-server-2008 |
| SQL Server 2012 | critical | SQL Server 2012 extended support ended on 12 July 2022. | https://learn.microsoft.com/lifecycle/products/microsoft-sql-server-2012 |
| SQL Server 2014 | critical | SQL Server 2014 extended support ended on 9 July 2024. | https://learn.microsoft.com/lifecycle/products/sql-server-2014 |
| SQL Server 2016 | critical | SQL Server 2016 extended support ended on 14 July 2026. | https://learn.microsoft.com/lifecycle/products/sql-server-2016 |
| SQL Server 2019 | warning | Mainstream support ended on 28 February 2025. Extended support, security fixes only, runs to 8 January 2030. | https://learn.microsoft.com/lifecycle/products/sql-server-2019 |
| Fauna | critical | The hosted Fauna service was shut down on 30 May 2025. | https://docs.fauna.com/fauna/current/eol-faq/ |
| Atlas Device Sync | critical | Atlas Device Sync was removed on 30 September 2025. | https://www.mongodb.com/docs/atlas/app-services/sync/device-sync-deprecation/ |
| Realm / Atlas Device SDKs | critical | Atlas Device SDKs were removed on 30 September 2025. Use SQLite on the device. | https://www.mongodb.com/docs/atlas/device-sdks/deprecation/ |
| Firebase Dynamic Links | critical | Firebase Dynamic Links shut down on 25 August 2025. | https://firebase.google.com/support/dynamic-links-faq |
| Universal Analytics | critical | Universal Analytics stopped processing hits in 2024. Use a current analytics product if you need one. | https://support.google.com/analytics/answer/11583528 |
| Google Cloud IoT Core | critical | Google Cloud IoT Core was retired. New IoT work should not target it. | https://cloud.google.com/iot/docs/release-notes |
| AWS CodeCommit | warning | AWS CodeCommit is closed to new customers. Use GitHub or another Git host. | https://docs.aws.amazon.com/codecommit/latest/userguide/welcome.html |
| CentOS Linux 7 | critical | CentOS Linux 7 ended on 30 June 2024. | https://www.centos.org/centos-linux-eol/ |
| Python 2 | critical | Python 2 reached end of life on 1 January 2020. | https://www.python.org/doc/sunset-python-2/ |
| PHP 7 | critical | PHP 7.4 security support ended on 28 November 2022. New work should use PHP 8.3 or newer. | https://www.php.net/supported-versions.php |
| PHP 5 | critical | PHP 5 is long past end of life. | https://www.php.net/supported-versions.php |
| Node.js 14 | critical | Node.js 14 is end of life. | https://github.com/nodejs/release#release-schedule |
| Node.js 16 | critical | Node.js 16 is end of life. | https://github.com/nodejs/release#release-schedule |
| Node.js 18 | critical | Node.js 18 is end of life. | https://github.com/nodejs/release#release-schedule |
| Windows Server 2012 | critical | Windows Server 2012 extended support ended on 10 October 2023. | https://learn.microsoft.com/lifecycle/products/windows-server-2012 |
| Ubuntu 16.04 | critical | Ubuntu 16.04 standard support is over. | https://ubuntu.com/about/release-cycle |
| Ubuntu 18.04 | critical | Ubuntu 18.04 standard support ended in 2023. Do not base a new deploy on it. | https://ubuntu.com/about/release-cycle |
| MongoDB 4.0 | critical | MongoDB 4.0 is end of life. | https://www.mongodb.com/legal/support-policy/lifecycles |
| MongoDB 4.4 | critical | MongoDB 4.4 is end of life. | https://www.mongodb.com/legal/support-policy/lifecycles |
| Gatsby Cloud | critical | Gatsby Cloud as a host is gone. This engine does not recommend it. | https://www.gatsbyjs.com/ |
| Parse.com | critical | The Parse.com hosted service shut down in 2017. | https://parseplatform.org/ |
| Heroku Postgres hobby | critical | Heroku removed its free and hobby database tiers. | https://devcenter.heroku.com/changelog |

## Regulatory sources

- RBI storage of payment system data, 6 April 2018: https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11244
- Digital Personal Data Protection Act, 2023: https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf
- Regulation (EU) 2016/679 (GDPR): https://eur-lex.europa.eu/eli/reg/2016/679/oj
- HHS HIPAA for professionals: https://www.hhs.gov/hipaa/for-professionals/index.html
- PCI DSS document library: https://www.pcisecuritystandards.org/document_library/
- ISO/IEC 27001: https://www.iso.org/standard/27001
