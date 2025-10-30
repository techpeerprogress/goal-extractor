from dashboard import main as dashboard_main

# Streamlit executes this file as a page module (not as __main__),
# so we call the dashboard entrypoint unconditionally.
dashboard_main()


