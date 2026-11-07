from datetime import datetime
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import uuid
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel