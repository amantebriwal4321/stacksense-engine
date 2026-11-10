# Demo narration

About two and a half minutes. Indian English, plain speech. Do not say the author's name.

This is StackSense, a local engine that recommends a tech stack from a project brief. The choice is rules and scores over a catalog of real products. The LLM switch stays off. There is no model call in this build. The same file in gives the same JSON out.

Start with the portfolio. One beginner, two weeks, zero dollars, and the pages have to rank. The engine returns Astro, no server, no database, on Cloudflare Pages. The cost band is zero. A container would be extra work for a site that is just Markdown.

Next, the home services marketplace. India residency and DPDP are hard constraints, so the database and the files stay in Bangalore. The team writes TypeScript, so the web is Next.js and the Android app is Expo, with one NestJS API. Chat, search, photos, and payments show up as supporting pieces. Razorpay takes the money. The SMS warning is explicit, because OTP can blow a 150 dollar budget even when the servers fit.

The whiteboard is a different shape. Five thousand people on one board, a hundred millisecond target, and GDPR. The engine puts a Go sync service on ECS in Frankfurt, React on the client, and Yjs for the shared document. It does not reach for Kubernetes.

The lending app locks the cloud to AWS and the region to Mumbai. The ledger is Postgres with a standby. Card data stays at Razorpay. The credit model is a SageMaker endpoint in the same region, not a public API. Backups are called out: they have to stay in India too.

The HR tool reuses what the company already runs. Entra ID for login. The existing SQL Server for the rows. The app is Razor Pages on Azure in Central India. SQL Server 2019 is past mainstream support, and the warning says so, but the engine does not force a migration in a six week MVP.

The crop survey is offline first. The phone keeps SQLite. Photos are shrunk before they hit a weak network. The API is a small Python service in Bangalore. Realm is not recommended. That sync product was shut down.

Two edges, quickly. A file with bad types and a priority of 9 returns invalid input and no stack. A fintech with a zero dollar budget is marked infeasible. The engine still shows the cheapest stack that respects RBI and AWS, and it prints the dollar gap. It does not pretend the budget is fine.

That is the demo. Run it with python -m stacksense serve, import a scenario, and export the JSON.
