import sys
import threading
import time
import traceback
from webbrowser import open as web

import FreeSimpleGUI as sg

from base import LINKS, VERSION, LoginException, Scraper, Udemy, scraper_dict
from images import *

sg.set_global_icon(icon)
sg.change_look_and_feel("dark")
sg.theme_background_color
sg.set_options(
    button_color=(sg.theme_background_color(), sg.theme_background_color()),
    border_width=0,
    font=10,
)

# Function to safely scrape a site with timeout and retry mechanisms
def safe_scraping_thread(site: str, timeout: int = 30, max_retries: int = 3):
    """
    This function wraps around create_scraping_thread to introduce
    timeout and retry logic for handling unresponsive scrapers.
    """
    retries = 0
    while retries < max_retries:
        try:
            thread = threading.Thread(target=create_scraping_thread, args=(site,))
            thread.start()
            thread.join(timeout)  # Timeout limit
            if thread.is_alive():
                raise TimeoutError(f"Scraping {site} timed out after {timeout} seconds.")
            break  # Success, exit loop
        except TimeoutError as te:
            retries += 1
            if retries < max_retries:
                print(f"Retrying {site} ({retries}/{max_retries}) due to timeout.")
            else:
                error_message = f"Scraping {site} failed after {max_retries} retries."
                main_window.write_event_value("Error", error_message)
                break
        except Exception as e:
            error_message = f"Unknown error in {site}: {str(e)}"
            main_window.write_event_value("Error", error_message)
            break

# Update the existing function to use threading with timeout
def create_scraping_thread(site: str):
    code_name = scraper_dict[site]
    main_window[f"i{site}"].update(visible=False)
    main_window[f"p{site}"].update(0, visible=True)

    try:
        scraper_thread = threading.Thread(target=getattr(scraper, code_name), daemon=True)
        scraper_thread.start()

        # Wait for the scraper to begin or detect an issue
        while getattr(scraper, f"{code_name}_length") == 0:
            time.sleep(0.1)  # Avoid busy waiting

        if getattr(scraper, f"{code_name}_length") == -1:
            raise Exception(f"Error in: {site}")

        main_window[f"p{site}"].update(0, max=getattr(scraper, f"{code_name}_length"))

        while not getattr(scraper, f"{code_name}_done") and not getattr(
            scraper, f"{code_name}_error"
        ):
            main_window[f"p{site}"].update(
                getattr(scraper, f"{code_name}_progress") + 1
            )
            time.sleep(0.1)  # Update every 0.1 seconds

        if getattr(scraper, f"{code_name}_error"):
            raise Exception(f"Error in: {site}")
    except Exception as e:
        error_message = getattr(scraper, f"{code_name}_error", "Unknown Error")
        main_window.write_event_value(
            "Error", f"{error_message}|:|Unknown Error in: {site} {VERSION}"
        )
    finally:
        main_window[f"p{site}"].update(0, visible=False)
        main_window[f"i{site}"].update(visible=True)


# Use the new safe_scraping_thread in the main scrape function
def scrape():
    try:
        for site in udemy.sites:
            main_window[f"pcol{site}"].update(visible=True)
        main_window["main_col"].update(visible=False)
        main_window["scrape_col"].update(visible=True)

        # Scraping process with safe mechanism
        for site in udemy.sites:
            safe_scraping_thread(site, timeout=30, max_retries=3)

        udemy.scraped_data = scraper.get_scraped_courses(create_scraping_thread)
        main_window["scrape_col"].update(visible=False)
        main_window["output_col"].update(visible=True)

        # ------------------------------------------
        udemy.start_enrolling()
        main_window["output_col"].Update(visible=False)
        main_window["done_col"].update(visible=True)

        main_window["se_c"].update(
            value=f"Successfully Enrolled: {udemy.successfully_enrolled_c}"
        )
        main_window["as_c"].update(
            value=f"Amount Saved: {round(udemy.amount_saved_c, 2)} {udemy.currency.upper()}"
        )
        main_window["ae_c"].update(
            value=f"Already Enrolled: {udemy.already_enrolled_c}"
        )
        main_window["e_c"].update(value=f"Expired Courses: {udemy.expired_c}")
        main_window["ex_c"].update(value=f"Excluded Courses: {udemy.excluded_c}")

    except Exception as e:
        traceback_str = traceback.format_exc()
        main_window.write_event_value(
            "Error",
            f"{traceback_str}\n\nVersion:{VERSION}\nLink:{getattr(udemy, 'link', 'None')}\nTitle:{getattr(udemy, 'title','None')}|:|Error g100",
        )


# Main UI loop remains the same
