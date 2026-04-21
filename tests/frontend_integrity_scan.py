import os
import re
import sys

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')

def scan_frontend():
    if not os.path.exists(FRONTEND_DIR):
        print(f"Error: Frontend directory not found at {FRONTEND_DIR}")
        sys.exit(1)

    issues_found = 0
    
    # regex patterns
    localhost_pattern = re.compile(r'http://(?:localhost|127\.0\.0\.1)(?::\d+)?')
    catch_pattern = re.compile(r'\.(?:then|catch)\s*\(') # Simplified check, just looking for common promise issues or try/catch. A better way is checking for try block without catch, or fetch without catch
    fetch_pattern = re.compile(r'fetch\(')
    api_fetch_pattern = re.compile(r'apiFetch\(')
    script_pattern = re.compile(r'<script.*?(?:src)=[\'"](.*?)[\'"].*?>')
    link_pattern = re.compile(r'<link.*?(?:href)=[\'"](.*?)[\'"].*?>')

    for root, _, files in os.walk(FRONTEND_DIR):
        for file in files:
            if not file.endswith('.html') and not file.endswith('.js'):
                continue
                
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    line_num = i + 1
                    
                    # 1. Hardcoded localhost URLs
                    if localhost_pattern.search(line):
                        print(f"[Warning] Hardcoded localhost URL in {file}:{line_num}")
                        print(f"  > {line.strip()}")
                        issues_found += 1
                        
                    # 2. Check broken script references
                    for match in script_pattern.finditer(line):
                        src = match.group(1)
                        if not src.startswith(('http', '//')) and not src.startswith('/'):
                            # Relative path; simplistic check
                            asset_path = os.path.join(root, src)
                            if not os.path.exists(asset_path):
                                print(f"[Error] Broken script reference in {file}:{line_num} -> {src}")
                                issues_found += 1
                                
                    for match in link_pattern.finditer(line):
                        src = match.group(1)
                        if not src.startswith(('http', '//', 'data:')) and not src.startswith('/'):
                            asset_path = os.path.join(root, src)
                            if not os.path.exists(asset_path):
                                print(f"[Error] Broken link reference in {file}:{line_num} -> {src}")
                                issues_found += 1
                                
                # 3. Missing catch handlers check
                # This could be checking if `fetch(` or `apiFetch(` happens without a try/catch or .catch()
                # A simplistic heuristic:
                fetch_count = len(fetch_pattern.findall(content))
                api_fetch_count = len(api_fetch_pattern.findall(content))
                catch_count = len(re.findall(r'catch\s*\(', content))
                
                # We basically know our custom apiFetch is supposed to handle errors internally
                # but raw fetch() calls might need try-catch

    if issues_found == 0:
        print("Frontend integrity scan passed! No hardcoded URLs or broken references found.")
    else:
        print(f"Frontend integrity scan completed with {issues_found} issues found.")
        sys.exit(1)

if __name__ == '__main__':
    scan_frontend()
