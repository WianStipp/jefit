"""
JEFITClient is a Python client for interacting with the JEFIT workout tracking website.

This module provides a JEFITClient class that can be used to retrieve workout data for a specific user,
and parse the data into the LiftingLog and ExerciseBlock Pydantic models.
Additionally it includes JEFITClientConfig and LiftingLog model classes.
"""
from typing import List
import bs4
import httpx
import pydantic
import re

USER_BASE_URL: str = 'https://www.jefit.com/user'
LOGS_BASE_URL: str = 'https://www.jefit.com/members/user-logs/log/'

class LiftingLog(pydantic.BaseModel):
  """
  A Pydantic model representing a single lifting set.

  Args:
    set_number (int): The set number of the lifting set
    weight (float): The weight used in the lifting set
    reps (int): The number of reps performed in the lifting set
  """
  set_number: int
  weight: float
  reps: int

class ExerciseBlock(pydantic.BaseModel):
  """
  A Pydantic model representing a single exercise.

  Args:
    exercise_name (str): The name of the exercise
    one_rep_max (float): The one rep max of the exercise
    lifting_logs (List[LiftingLog]): A list of LiftingLog objects representing the sets of the exercise
  """
  exercise_name: str
  one_rep_max: float
  lifting_logs: List[LiftingLog]

class JEFITClientConfig(pydantic.BaseModel):
  """
  A Pydantic model representing the url configuration for the client.

  Args:
    user_base_url (str): The base URL for the JEFIT user profile page.
    logs_base_url (str): The base URL for the JEFIT user logs page.
  """
  user_base_url: str
  logs_base_url: str

DEFAULT_JEFIT_CONFIG = JEFITClientConfig(user_base_url=USER_BASE_URL, logs_base_url=LOGS_BASE_URL)

class JEFITClient:
  """
  A class representing a client for interacting with the JEFIT website.

  Attributes:
    url_config (JEFITClientConfig): A JEFITClientConfig object that contains the base urls to access the user and logs pages.
  """
  def __init__(self, url_config = DEFAULT_JEFIT_CONFIG) -> None:
    self.url_config = url_config
  
  def get_workout_from_date(self, username: str, date: str):
    """Get the data from a workout of a specific date."""
    with httpx.Client() as session:
      response = session.get(self.url_config.logs_base_url, params={"xid": username, "dd": date})
    response.raise_for_status()
    soup = bs4.BeautifulSoup(response.content, "html.parser")
    workout = soup.find(id='logList1')
    exercises = workout.findAll('div', class_='exercise-block')
    exercise_blocks: List[ExerciseBlock] = []
    for exercise in exercises:
      blocks = exercise.find('div', class_='fixedLogBar').findAll('div', class_='fixedLogBarBlock align-top')
      assert len(blocks) == 4
      picture, name, onerepmax, liftinglogs = blocks
      name = name.find('a').get_text().strip()
      onerepmax = float(onerepmax.get_text())
      liftinglogs = parse_to_lifting_log(liftinglogs.get_text())
      exercise_blocks.append(ExerciseBlock(exercise_name=name, one_rep_max=onerepmax, lifting_logs=liftinglogs))
    return exercise_blocks

def parse_to_lifting_log(liftinglogs: str) -> LiftingLog:
    """
    Parses a string of lifting logs into a list of LiftingLog objects.

    Args:
      liftinglogs (str): A string containing the lifting logs in the format "Set 1 : 70x5 Set 2 : 70x5 Set 3 : 70x5"

    Returns:
      List[LiftingLog]: A list of LiftingLog objects, where each object contains the set number, weight, and reps for a single set.
    """
    pattern = re.compile(r'Set (\d+) : (\d+)x(\d+)')
    return [LiftingLog(set_number=set_, weight=weight, reps=reps) for set_, weight, reps in pattern.findall(liftinglogs)]

if __name__ == "__main__":
  cli = JEFITClient()
  results = cli.get_workout_from_date('wstipp', '2023-01-14')
  for r in results:
    print(r)
    print()
