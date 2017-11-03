# -*- coding: utf-8 -*-

import click
import difflib
import email.mime.text
import html.parser
import os.path
import requests
import smtplib

@click.command()
@click.option('--output-file', type=click.Path(readable=True, writable=True), default='aws-hipaa-service.txt')
@click.option('--silent/--not-silent', default=False)
def cli(output_file, silent):
    resp = requests.get('https://aws.amazon.com/compliance/hipaa-eligible-services-reference/')
    resp.raise_for_status()

    current_content = []
    add_lines = False
    for l in resp.content.splitlines():

        if b'Last Updated: ' in l:
            current_content.append(strip_tags(str(l, 'utf-8')).strip())
            add_lines = True
            continue

        if add_lines and b'HIPAA' in l:
            break

        if add_lines and l.strip():
            stripped = strip_tags(str(l, 'utf-8')).strip()
            if stripped:
                current_content.append(stripped)

    prev_content = []
    if os.path.exists(output_file):
        with open(output_file, 'r') as fp:
            prev_content = [l.strip() for l in fp.readlines()]

    with open(output_file, 'w') as fp:
        for l in current_content:
            fp.write(l + '\n')

    diff = list(difflib.unified_diff(prev_content, current_content))
    if not diff:
        if not silent:
            click.echo('No changes')
    else:
        from_addr = 'thomas@98point6.com'
        to_addr = 'thomas@98point6.com'
        diff_str = '\n'.join(diff[3:])
        if not silent:
            click.echo('Changes detected; emailing {}'.format(to_addr))
            click.echo(diff_str)

        msg = email.mime.text.MIMEText('AWS updated HIPAA services: \n\n' + diff_str)
        msg['Subject'] = 'AWS updated HIPAA services'
        msg['From'] = from_addr
        msg['To'] = to_addr
        smtp = None
        try:
            smtp = smtplib.SMTP('localhost')
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
            if not silent:
                click.echo('Sent email')
        except:
            click.echo(msg.as_string())
        finally:
            if smtp is not None:
                smtp.quit()


class MLStripper(html.parser.HTMLParser):
    def __init__(self):
        html.parser.HTMLParser.__init__(self, convert_charrefs=False)
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def handle_entityref(self, name):
        self.fed.append('&%s;' % name)

    def handle_charref(self, name):
        self.fed.append('&#%s;' % name)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(value):
    s = MLStripper()
    s.feed(value)
    s.close()
    return s.get_data()


if __name__ == '__main__':
    cli()
