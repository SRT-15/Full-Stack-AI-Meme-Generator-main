from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
from AIMemeGenerator import generate

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'Outputs'

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_prompt = request.form['user_prompt']
        meme_count = int(request.form['meme_count'])
        
        # Generate multiple memes
        meme_results = generate(
            user_entered_prompt=user_prompt,
            meme_count=meme_count,
            noUserInput=True,
            noFileSave=False
        )
        
        # Collect all generated filenames
        meme_filenames = [meme['file_name'] for meme in meme_results]
        
        # Redirect to result page with all filenames
        return redirect(url_for('result', 
                              meme_filenames=','.join(meme_filenames),
                              user_prompt=user_prompt,
                              meme_count=meme_count,
                              meme_index=0))  # Start with first meme
    
    # Get previous inputs for regeneration
    prefill = {
        'user_prompt': request.args.get('user_prompt', ''),
        'meme_count': request.args.get('meme_count', '1')
    }
    return render_template('index.html', prefill=prefill)

@app.route('/result')
def result():
    meme_filenames = request.args.get('meme_filenames', '').split(',')
    meme_index = int(request.args.get('meme_index', 0))
    user_prompt = request.args.get('user_prompt')
    meme_count = int(request.args.get('meme_count', 1))
    
    # Handle index wrapping for continuous cycling
    meme_index = meme_index % len(meme_filenames)
    current_meme = meme_filenames[meme_index]
    
    return render_template('result.html',
                         current_meme=current_meme,
                         meme_filenames=meme_filenames,
                         meme_index=meme_index,
                         user_prompt=user_prompt,
                         meme_count=meme_count)

@app.route('/outputs/<filename>')
def outputs(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True,
        download_name=f"meme_{filename}"
    )

if __name__ == '__main__':
    app.run(debug=True)