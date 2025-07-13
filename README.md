## Getting Started

1. **Create a directory and virtual environment**: Set up a virtual environment

    ```bash
    git clone (this repo)
    cd StreetEasiest
    python3 -m venv env
    source env/bin/activate
    ```

2. **Install Project Dependencies**: Install the project's dependencies into a virtual environment.

    ```bash
    pip install -r requirements.txt
    ```

All commands from now on should be run from inside the virtual environment.

3. **Load Dummy Data**: Load in some dummy data to populate the site with some content.

    ```bash
    make load-data
    ```

4. **Start the Server**: Start the Django development server.

    ```bash
    make start
    ```

5. **Access the Site and Admin**: Once the server is running, you can view the site at `localhost:8000` and access the Wagtail admin interface at `localhost:8000/admin`. Log in with the default credentials provided by :

    - Username: admin
    - Password: ?


