const fs = require('fs');
const path = require('path');

const publicAssetsDir = path.join(__dirname, '..', 'public', 'assets');

if (fs.existsSync(publicAssetsDir)) {
    const files = fs.readdirSync(publicAssetsDir);
    files.forEach(file => {
        if (file.match(/^index\..*\.(js|css)$/)) {
            fs.unlinkSync(path.join(publicAssetsDir, file));
        }
    });
}
