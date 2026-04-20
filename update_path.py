import pathlib
p = pathlib.Path('test_model_direct.py')
content = p.read_text()
content = content.replace('checkpoints/best_model.pt', 'checkpoints/real_data/best_model.pt')
p.write_text(content)
print('Updated test_model_direct.py')
