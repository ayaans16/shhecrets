# s(hh)ecrets
The motto is: two can keep a secret if one of them is dead, but no need to be gruesome because your secrets are safe with shhecrets.
## About the Application
In collaborative projects such as hackathons, group projects, tasks and building ideas, the usage of sensitive information is very normal. Whether that be your MySQL server credentials, your API keys, or an entire `.env` file that needs to be shared. To decrease the risk of exposing your information, shhecrets helps to privately pass this information without storing any of it, ensuring your credentials are safe and securely passed over.

> [!TIP]
> Check it out: **https://shhecrets.ca/**

## How It Works
```mermaid
flowchart TD
    A[Open web app] -->|Switch theme| B(Create a session)
    B --> C[Input secret credentials]
    C --> L[Copy link]
    L -->|Feature #1| D[Send to one user]
    L -->|Feature #2| E[One time-link]
    L -->|Feature #3| F[Expires in ~10 mins]
```

## Project Architecture
```mermaid
flowchart LR
    subgraph app[Live App: User Session Flow]
        A[Browser generates key,<br/>POST /sessions] --> B[Backend writes Redis meta key<br/>+ Mongo audit doc]
    end

    subgraph ci[CI: on every push / PR]
        Test[pytest + tsc + vitest + shellcheck] --> Gate{All pass?}
    end

    subgraph cd[CD: only on push to main]
        Deploy[SSH to VPS:<br/>git pull + docker-compose up --build] --> Verify[curl real public<br/>health endpoint]
    end

    Gate -->|yes, and on main| Deploy
    Gate -->|no| Fail[Blocked - fix and repush]
```



