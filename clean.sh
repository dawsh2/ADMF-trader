for file in *.py; do 
  if [ "$file" != "main.py" ]; then 
    mv "$file" _archived/
  fi
done
